# LearnSphere


## Environment Variables

Create a `.env` file in your project root with the following content:

```env
MISTRAL_API_KEY=
OPENAI_API_KEY=
QDRANT_URL=http://localhost:6333
QDRANT_HOST=localhost
QDRANT_PORT=6333
UPLOAD_DIR=./uploads
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```
Installation
1. Clone the Repository
```bash
git clone https://github.com/your-username/RAG_ChatBot.git
cd RAG_ChatBot
```
2. Install Dependencies
```bash
pip install -r requirements.txt
```
3. Start Qdrant (Vector Database)
```bash
docker-compose up -d
```
4. Start the Backend (FastAPI)
```bash
python run_api.py
```
5. Start the Frontend (Streamlit)

Admin interface:

```bash
Copy code
streamlit run frontend/admin_app.py
```
User interface:

```bash
Copy code
streamlit run frontend/user_app.py
```
