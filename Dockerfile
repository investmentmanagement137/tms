# Use Apify's Python + Chrome base image
FROM apify/actor-python-chrome:3.11

# Set working directory
WORKDIR /usr/src/app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . ./

# Set the entry point to the main script
CMD ["python", "-u", "main.py"]
