# Orbit AI Chatbot Platform

Orbit AI is a beautiful, easy-to-use platform where anyone can build their own AI chatbots. Users can sign up, create their own AI agents, upload files to teach the AI new things, and chat with it instantly. It is powered by **Groq** for super-fast replies and **Cohere** so the AI can read and understand the documents you upload.

## 🚀 Key Features
- **User Accounts**: Safely sign up and log in.
- **Private Workspaces**: Create your own separate AI assistants.
- **Custom Rules**: Tell your AI exactly how to behave.
- **File Uploads (Cohere)**: Upload PDFs, text files, and more. The AI will read them and use them to answer your questions.
- **Super Fast Chat (Groq)**: Get answers from the AI almost instantly.
- **Beautiful Design**: A modern dark mode with smooth animations.

## 📚 Project Documents
- **Architecture**: Read [ARCHITECTURE.md](./ARCHITECTURE.md) to see how we made the app fast, safe, and easy to grow.


## 🛠️ How to Run This on Your Computer

1. Set up your Python virtual environment.
2. Install the required packages: 
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the main folder and add your secret keys:

   ```env
   DJANGO_SECRET_KEY=change-this-in-production
   GROQ_API_KEY=gsk_your_groq_key
   GROQ_MODEL=llama-3.3-70b-versatile
   COHERE_API_KEY=your_cohere_key
   COHERE_EMBED_MODEL=embed-v4.0
   CHROMA_PATH=./chroma_data
   ```

4. Set up the database and start the app:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

5. Open your web browser and go to `http://127.0.0.1:8000`. Create an account and start building your AI!

