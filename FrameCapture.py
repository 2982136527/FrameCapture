from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import cv2
import os
import random
import logging
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # 允许跨域，方便本地测试

# 配置日志记录器，记录级别设为DEBUG方便查看关键信息
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_video_path_from_strm(strm_file_path):
    try:
        with open(strm_file_path, 'r') as file:
            logger.debug(f"正在读取.strm文件: {strm_file_path}")
            video_path = file.read().strip()
            return video_path
        logger.error(f"读取.strm文件 {strm_file_path} 出现异常，未正常返回视频路径。")
    except Exception as e:
        logger.error(f"读取.strm文件 {strm_file_path} 出现异常: {e}")
        socketio.emit('log', f"读取.strm文件 {strm_file_path} 出现异常: {e}")
        return None


def capture_random_frame(strm_file_path, video_path, output_folder, generate_fanart, generate_poster, interval_time):
    try:
        # 获取.strm文件的文件名（不含后缀）
        strm_file_name = os.path.splitext(os.path.basename(strm_file_path))[0]

        fanart_path = os.path.join(output_folder, f"{strm_file_name}.jpg")
        poster_path = os.path.join(output_folder, f"{strm_file_name}.jpg")

        # 检测文件是否存在
        fanart_exists = os.path.exists(fanart_path)
        poster_exists = os.path.exists(poster_path)

        logger.info(f"检测到 {fanart_path} 存在：{fanart_exists}")
        logger.info(f"检测到 {poster_path} 存在：{poster_exists}")

        # 如果fanart已存在，直接跳过fanart生成相关操作，返回True表示当前文件此部分无需处理
        if fanart_exists:
            logger.info(f"{strm_file_path} 的图片已存在，直接跳过fanart生成。")
            return True

        # 如果poster已存在，直接跳过poster生成相关操作，返回True表示当前文件此部分无需处理
        if poster_exists:
            logger.info(f"{strm_file_path} 的图片已存在，直接跳过poster生成。")
            return True

        # 以下是需要视频读取和截图的情况
        if not os.path.exists(output_folder):
            logger.debug(f"输出文件夹 {output_folder} 不存在，准备创建。")
            os.makedirs(output_folder)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"错误：无法打开视频 {video_path}。")
            socketio.emit('log', f"错误：无法打开视频 {video_path}。")
            return False

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            logger.error(f"错误：视频 {video_path} 没有帧。")
            socketio.emit('log', f"错误：视频 {video_path} 没有帧。")
            cap.release()
            return False

        # 随机选择帧
        start_frame = total_frames // 2
        random_frame_fanart = random.randint(start_frame, total_frames - 1)
        random_frame_poster = random.randint(start_frame, total_frames - 1)
        while random_frame_poster == random_frame_fanart:
            random_frame_poster = random.randint(start_frame, total_frames - 1)

        # 捕获fanart帧
        if generate_fanart:
            cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_fanart)
            ret_fanart, frame_fanart = cap.read()
            if ret_fanart:
                cv2.imwrite(fanart_path, frame_fanart)
                logger.info(f"成功截取 {strm_file_name} 的poster帧，保存路径为 {poster_path}")  # 添加成功日志提示
                socketio.emit(f"成功截取 {strm_file_name} 的poster帧，保存路径为 {poster_path}")
            else:
                logger.error(f"无法读取视频 {video_path} 的第 {random_frame_fanart} 帧用于生成fanart。")
                socketio.emit('log', f"无法读取视频 {video_path} 的第 {random_frame_fanart} 帧用于生成fanart。")

        # 捕获poster帧
        if generate_poster:
            cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_poster)
            ret_poster, frame_poster = cap.read()
            if ret_poster:
                height, width = frame_poster.shape[:2]
                new_width = min(width, int(height * (2 / 3)))
                new_height = int(new_width * (3 / 2))
                start_x = (width - new_width) // 2
                start_y = (height - new_height) // 2
                poster_frame = frame_poster[start_y:start_y + new_height, start_x:start_x + new_width]
                cv2.imwrite(poster_path, poster_frame)
                logger.info(f"成功截取 {strm_file_name} 的poster帧，保存路径为 {poster_path}")  # 添加成功日志提示
                socketio.emit(f"成功截取 {strm_file_name} 的poster帧，保存路径为 {poster_path}")
            else:
                logger.error(f"无法读取视频 {video_path} 的第 {random_frame_poster} 帧用于生成poster。")
                socketio.emit('log', f"无法读取视频 {video_path} 的第 {random_frame_poster} 帧用于生成poster。")

        cap.release()
        return True

    except Exception as e:
        logger.error(f"处理视频帧截取时出现异常: {e}")
        socketio.emit('log', f"处理视频帧截取时出现异常: {e}")
        return False


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/capture', methods=['POST'])
def capture_video_frames():
    data = request.get_json()
    generate_fanart = data.get('generateFanart', False)
    generate_poster = data.get('generatePoster', False)
    folder_path = data.get('folder_path', "strm")
    interval_time = data.get('interval_time', 0)  # 获取间隔时间，默认0秒
    logs = []
    status ='success'

    try:
        logger.debug(f"开始遍历文件夹 {folder_path} 查找.strm文件。")
        for root_dir, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.strm'):
                    strm_file_path = os.path.join(root_dir, file)
                    video_path = get_video_path_from_strm(strm_file_path)
                    if video_path is None:
                        logs.append(f"处理文件 {strm_file_path} 的结果：失败（获取视频路径失败）")
                        continue
                    result = capture_random_frame(strm_file_path, video_path, root_dir, generate_fanart, generate_poster,
                                                  interval_time)
                    if not result:
                        status = 'failed'
                    logs.append(f"处理文件 {strm_file_path} 的结果：{'成功' if result else '失败'}")
    except Exception as e:
        status = 'failed'
        logger.error(f"遍历文件出现异常: {e}")
        logs.append(f"出现异常: {e}")

    return jsonify({
       'status': status,
        'logs': logs
    })


@app.route('/get_subfolders', methods=['GET'])
def get_subfolders():
    base_folder = "strm"
    subfolders = []
    for root, dirs, _ in os.walk(base_folder):
        for dir in dirs:
            subfolders.append(os.path.join(root, dir))
    return jsonify(subfolders)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)