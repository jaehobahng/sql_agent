FROM python:3.11-slim

# Set environment variable to ensure Python output is logged
ENV PYTHONUNBUFFERED=1

# Copy requirements.txt first to leverage Docker's cache
COPY requirements.txt /app/requirements.txt

# Set the working directory
WORKDIR /app

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Default command
CMD ["python", "script.py"]

# # Healthcheck to confirm the data insertion has completed
# HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=5 \
#   CMD [ "/bin/sh", "-c", "[ -f /app/data_loaded.flag ] || exit 1" ]