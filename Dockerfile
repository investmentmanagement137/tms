# Use Apify's Python + Selenium base image (includes Chrome)
FROM apify/actor-python-selenium:3.11

# Set working directory
WORKDIR /usr/src/app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . ./

# Set the entry point to the main script
CMD ["python", "-u", "main.py"]
