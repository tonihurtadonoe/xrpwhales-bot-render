# -----------------------------
# Base image: Python 3.11 slim
# -----------------------------
FROM python:3.11-slim

# -----------------------------
# Set working directory
# -----------------------------
WORKDIR /app

# -----------------------------
# Copy requirements and install
# -----------------------------
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Copy app code
# -----------------------------
COPY . .

# -----------------------------
# Environment variables
# -----------------------------
# Puedes definir defaults si quieres
ENV PORT=10000
ENV CHECK_INTERVAL=60

# -----------------------------
# Expose port for Render
# -----------------------------
EXPOSE 10000

# -----------------------------
# Run the bot
# -----------------------------
CMD ["python", "xrp_whales_bot.py"]
