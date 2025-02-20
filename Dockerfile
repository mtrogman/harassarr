FROM python:3.12
WORKDIR /app

# Copy requirements.txt from build machine to WORKDIR (/app) folder 
COPY requirements.txt requirements.txt

# Install Python requirements
RUN pip3 install --no-cache-dir -r requirements.txt

# Make Docker /config volume for optional config file
VOLUME /config

# Copy example config file from build machine to Docker /config folder
COPY config.* /config/

# Copy source code from build machine to WORKDIR (/app) folder
COPY . .

# Delete unnecessary files in WORKDIR (/app) folder (not caught by .dockerignore)
RUN echo "**** removing unneeded files ****"
RUN rm -rf /app/requirements.txt

CMD [ "python", "harassarr.py" ]