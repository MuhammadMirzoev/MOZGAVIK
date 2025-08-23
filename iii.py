import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter


# --- функция для чтения PDF ---
def read_pdf(file):
    pdf = PdfReader(file)
    text = ""
    for page in pdf.pages:
        text += page.extract_text() + "\n"
    return text


# --- Streamlit UI ---
st.title("📖 Читалка PDF (с чанками через LangChain)")

uploaded_file = st.file_uploader("Загрузите PDF книгу", type=["pdf"])

if uploaded_file:
    st.success("Файл загружен!")

    # Извлекаем текст
    text = read_pdf(uploaded_file)
    st.write(f"Общий объем текста: {len(text)} символов")

    # Разбиваем на чанки через LangChain
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,  # размер чанка
        chunk_overlap=200,  # перекрытие
        length_function=len
    )
    chunks = splitter.split_text(text)

    st.write(f"Количество чанков: {len(chunks)}")

    # Навигация по чанкам
    selected_chunk = st.number_input("Выберите номер чанка", 1, len(chunks), 1)
    st.text_area("Текст чанка", chunks[selected_chunk - 1], height=300)
