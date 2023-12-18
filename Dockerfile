# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /usr/src/app

# Install tmux and SSH client
RUN apt-get update && apt-get install -y tmux openssh-client

# Copy the current directory contents into the container at /usr/src/app
COPY cli.py /usr/src/app
COPY requirements.txt /usr/src/app
COPY init.sh /usr/src/app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Give execution rights on the init script
RUN chmod +x /usr/src/app/init.sh

# Run init.sh when the container launches
CMD ["/usr/src/app/init.sh"]
