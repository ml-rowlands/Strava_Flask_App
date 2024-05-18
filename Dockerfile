# Use the Miniconda3 image from ContinuumIO
FROM continuumio/miniconda3

# Set the working directory in the container
WORKDIR /app

# Copy the environment.yml file into the container
COPY environment.yml .

# Create the environment
RUN conda env create -f environment.yml

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "strava_app", "/bin/bash", "-c"]

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=development

# Expose port 5000 to the outside world
EXPOSE 5000

# Run the Flask app
CMD ["conda", "run", "--no-capture-output", "-n", "strava_app", "flask", "run"]
