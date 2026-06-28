import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile

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
        with st.spinner("Đang chuẩn bị video để xử lý..."):
            # Tạo file tạm trên ổ đĩa do Gemini SDK cần đường dẫn file vật lý
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
                temp_file.write(uploaded_file.read())
                temp_file_path = temp_file.name
        
        try:
            # Upload video lên Gemini
            with st.spinner("Đang tải video lên hệ thống của Google (tùy thuộc vào dung lượng, quá trình này có thể mất thời gian)..."):
                video_file = genai.upload_file(path=temp_file_path)
            
            # Kiểm tra trạng thái xử lý video trên hệ thống Google
            with st.spinner("Đang đợi hệ thống Google phân tích dữ liệu video (hình ảnh và âm thanh)..."):
                while video_file.state.name == "PROCESSING":
                    time.sleep(5)
                    video_file = genai.get_file(video_file.name)
                
            if video_file.state.name == "FAILED":
                st.error("Rất tiếc, đã xảy ra lỗi trong quá trình Google phân tích video của bạn.")
            else:
                st.success("Video đã được phân tích xong! Bắt đầu tạo tóm tắt...")
                
                # Gọi mô hình để tóm tắt
                with st.spinner("Đang tạo tóm tắt..."):
                    # Sử dụng mô hình gemini-2.5-flash
                    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
                    
                    prompt = "Hãy xem kỹ toàn bộ video này (cả hình ảnh và âm thanh) và cung cấp một bản tóm tắt thật chi tiết bằng tiếng Việt về những nội dung chính xuất hiện trong video."
                    
                    response = model.generate_content([video_file, prompt],
                                                      request_options={"timeout": 600}) # Đặt timeout cao cho video dài
                    
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
                genai.delete_file(video_file.name)

        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {e}")
        
        finally:
            # Xóa file tạm trên máy tính sau khi xử lý xong hoặc lỗi
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    pass
