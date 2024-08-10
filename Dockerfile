# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files to disc
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /phonebook

# Copy the requirements file into the container at /app
COPY requirements.txt /phonebook/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /phonebook/

# Copy the database initialization script
COPY init_db.py /phonebook/

# Initialize the database
RUN python init_db.py

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Set the FLASK_APP environment variable
ENV FLASK_APP=app:app

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]
