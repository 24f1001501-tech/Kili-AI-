# Backend (and a copy of the frontend) for a Hugging Face Docker Space.
# The website itself is served by Vercel, which forwards /api/* here.
FROM python:3.12-slim

RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    SAYBETTER_DATA_DIR=/home/user/app/backend/var \
    ALLOW_PROFILE_LIST=0
WORKDIR /home/user/app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=user . .
USER user

# Bake the 1.2 GB phoneme model into the image so the app starts quickly.
RUN python -c "from huggingface_hub import hf_hub_download; from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC; \
m='facebook/wav2vec2-xlsr-53-espeak-cv-ft'; hf_hub_download(m, 'vocab.json'); \
Wav2Vec2FeatureExtractor.from_pretrained(m); Wav2Vec2ForCTC.from_pretrained(m)"

WORKDIR /home/user/app/backend
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
