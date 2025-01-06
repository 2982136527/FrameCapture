import cv2
import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
from tkinter.scrolledtext import ScrolledText

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.widget.configure(state='normal')  
        self.widget.insert(tk.END, msg + '\n')  
        self.widget.see(tk.END) 
        self.widget.update_idletasks() 
        self.widget.configure(state='disabled') 

class LogViewer(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.log_text = ScrolledText(parent, wrap='word', state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.logger = logging.getLogger('tkinter_log_viewer')
        self.logger.setLevel(logging.DEBUG)
        self.text_handler = TextHandler(self.log_text)
        self.logger.addHandler(self.text_handler)

    def log_message(self, message, level=logging.INFO):
        self.logger.log(level, message)

def get_video_path_from_strm(strm_file_path):
    # 读取.strm文件并获取视频路径
    with open(strm_file_path, 'r') as file:
        video_path = file.read().strip()
    return video_path

def capture_random_frame(video_path, output_folder, generate_fanart, generate_poster, logger):
    # 创建输出文件夹（如果不存在）
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        logger.error(f"错误：无法打开视频 {video_path}。")
        return
    
    # 获取视频总帧数
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames == 0:
        logger.error(f"错误：视频 {video_path} 没有帧。")
        cap.release()
        return
    
    # 随机选择两个不同的帧，从视频的一半开始
    start_frame = total_frames // 2
    random_frame1 = random.randint(start_frame, total_frames - 1)
    random_frame2 = random.randint(start_frame, total_frames - 1)
    
    # 确保两个帧不相同
    while random_frame2 == random_frame1:
        random_frame2 = random.randint(start_frame, total_frames - 1)
    
    # 设置视频捕获到第一个随机帧
    cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame1)
    ret1, frame1 = cap.read()
    
    # 设置视频捕获到第二个随机帧
    cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame2)
    ret2, frame2 = cap.read()
    
    if generate_fanart and ret1:
        # 保存第一个帧为fanart.jpg
        fanart_path = os.path.join(output_folder, 'fanart.jpg')
        if os.path.exists(fanart_path):
            os.remove(fanart_path)  # 如果文件已存在，先删除
        cv2.imwrite(fanart_path, frame1)
        logger.info(f"帧已捕获并保存到 {fanart_path}")
    elif not ret1:
        logger.error(f"错误：无法读取视频 {video_path} 的第 {random_frame1} 帧。")

    if generate_poster and ret2:
        # 获取帧的尺寸
        height, width = frame2.shape[:2]
        
        # 计算2:3比例的区域
        new_width = min(width, int(height * (2/3)))
        new_height = int(new_width * (3/2))
        
        # 计算截取区域的起始点
        start_x = (width - new_width) // 2
        start_y = (height - new_height) // 2
        
        # 截取2:3比例的区域
        poster_frame = frame2[start_y:start_y+new_height, start_x:start_x+new_width]
        
        # 保存截取后的帧为poster.jpg
        poster_path = os.path.join(output_folder, 'poster.jpg')
        if os.path.exists(poster_path):
            os.remove(poster_path)  # 如果文件已存在，先删除
        cv2.imwrite(poster_path, poster_frame)
        logger.info(f"帧已捕获并保存到 {poster_path}")
    elif not ret2:
        logger.error(f"错误：无法读取视频 {video_path} 的第 {random_frame2} 帧。")
    
    cap.release()

def select_generation_options(log_viewer):
    generate_fanart_var = tk.BooleanVar()
    generate_poster_var = tk.BooleanVar()

    tk.Label(log_viewer, text="选择你想要生成的图像：").pack(pady=10)
    tk.Checkbutton(log_viewer, text="生成fanart", variable=generate_fanart_var).pack()
    tk.Checkbutton(log_viewer, text="生成poster", variable=generate_poster_var).pack()

    def confirm_selection():
        generate_fanart = generate_fanart_var.get()
        generate_poster = generate_poster_var.get()
        folder_path = filedialog.askdirectory(title="选择包含STRM文件的文件夹")
        if folder_path:
            # 递归遍历文件夹及其子文件夹中的所有.strm文件
            for root_dir, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith('.strm'):
                        strm_file_path = os.path.join(root_dir, file)
                        video_path = get_video_path_from_strm(strm_file_path)
                        capture_random_frame(video_path, root_dir, generate_fanart, generate_poster, log_viewer.logger)
            messagebox.showinfo("提示", "处理完成。")
        else:
            messagebox.showinfo("提示", "未选择文件夹。退出。")

    tk.Button(log_viewer, text="确认", command=confirm_selection).pack(pady=20)

def main():
    root = tk.Tk()
    root.title("日志查看器")
    root.geometry("800x600")
    
    log_viewer = LogViewer(root)
    log_viewer.pack(fill=tk.BOTH, expand=True)
    
    select_generation_options(log_viewer)
    
    root.mainloop()

if __name__ == "__main__":
    main()
