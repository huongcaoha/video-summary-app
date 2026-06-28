import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile
from moviepy.editor import VideoFileClip
# Cấu hình giao diện Streamlit
st.set_page_config(page_title="Công cụ tóm tắt Video với Gemini", page_icon="🎥", layout="centered")

st.title("🎥 Công cụ tóm tắt Video thông minh")
st.markdown("Tải video của bạn lên, hệ thống sẽ sử dụng AI của Google (Gemini) để phân tích hình ảnh & âm thanh và tóm tắt lại nội dung cho bạn!")

# 1. Yêu cầu người dùng nhập API Key
api_key = st.text_input("Nhập Google Gemini API Key của bạn:", type="password", help="Bạn có thể lấy API Key tại https://aistudio.google.com/app/apikey")

if not api_key:
    st.warning("Vui lòng nhập API Key để tiếp tục.")
    st.stop()

# Cấu hình API Key cho thư viện
genai.configure(api_key=api_key)

# 2. Xử lý Upload file video
uploaded_file = st.file_uploader("Chọn một file video để tóm tắt...", type=["mp4", "mov", "avi", "mkv"])

if uploaded_file is not None:
    # Hiển thị video để người dùng xem trước (tuỳ chọn)
    st.video(uploaded_file)
    
    # Nút bắt đầu xử lý
    if st.button("Bắt đầu Tóm tắt", type="primary"):
        temp_video_path = None
        temp_audio_path = None
        
        with st.spinner("Đang chuẩn bị và trích xuất âm thanh từ video để tiết kiệm token..."):
            # Tạo file tạm trên ổ đĩa do Gemini SDK cần đường dẫn file vật lý
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
                temp_file.write(uploaded_file.read())
                temp_video_path = temp_file.name
                
            try:
                # Trích xuất âm thanh từ video bằng moviepy
                video_clip = VideoFileClip(temp_video_path)
                
                # Tạo file tạm cho audio (.mp3)
                audio_file_descriptor, temp_audio_path = tempfile.mkstemp(suffix=".mp3")
                os.close(audio_file_descriptor) # Đóng để moviepy có quyền ghi vào file
                
                # Ghi file audio
                video_clip.audio.write_audiofile(temp_audio_path, logger=None)
                video_clip.close()
                
            except Exception as e:
                st.error(f"Lỗi khi trích xuất âm thanh: {e}")
                st.stop()
        
        try:
            # Upload âm thanh lên Gemini
            with st.spinner("Đang tải âm thanh lên hệ thống của Google (nhanh hơn nhiều so với tải video)..."):
                media_file = genai.upload_file(path=temp_audio_path)
            
            # Kiểm tra trạng thái xử lý trên hệ thống Google
            with st.spinner("Đang đợi hệ thống Google phân tích dữ liệu âm thanh..."):
                while media_file.state.name == "PROCESSING":
                    time.sleep(5)
                    media_file = genai.get_file(media_file.name)
                
            if media_file.state.name == "FAILED":
                st.error("Rất tiếc, đã xảy ra lỗi trong quá trình Google phân tích âm thanh của bạn.")
            else:
                st.success("Âm thanh đã được phân tích xong! Bắt đầu tạo tóm tắt...")
                
                # Gọi mô hình để tóm tắt
                with st.spinner("Đang tạo tóm tắt..."):
                    # Sử dụng mô hình gemini-2.5-flash
                    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
                    
                    prompt = "Hãy nghe kỹ toàn bộ đoạn âm thanh này và cung cấp một bản tóm tắt thật chi tiết bằng tiếng Việt về những nội dung chính."
                    
                    response = model.generate_content([media_file, prompt],
                                                      request_options={"timeout": 600}) # Đặt timeout cao cho audio dài
                    
                st.markdown("### 📝 Kết quả Tóm Tắt:")
                summary_text = response.text
                st.write(summary_text)
                
                # Nút download file TXT
                st.download_button(
                    label="Tải kết quả xuống (TXT)",
                    data=summary_text,
                    file_name="tom_tat_video.txt",
                    mime="text/plain",
                )
                
                # Tùy chọn: Xóa file trên Google sau khi dùng xong để tiết kiệm dung lượng
                genai.delete_file(media_file.name)

        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {e}")
        
        finally:
            # Xóa file tạm trên máy tính sau khi xử lý xong hoặc lỗi
            if temp_video_path and os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except Exception as e:
                    pass
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except Exception as e:
                    pass
