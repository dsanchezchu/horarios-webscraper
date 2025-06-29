provider "aws" {
  region = "us-east-2"
}

resource "aws_key_pair" "deployer" {
  key_name   = "deployer-key"
  public_key = file("C:/Users/Usuario/.ssh/id_rsa.pub")
}

resource "aws_security_group" "allow_ssh_streamlit" {
  name        = "allow_ssh_streamlit"
  description = "Allow SSH and Streamlit"

  ingress {
    description      = "SSH"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }

  ingress {
    description      = "Streamlit"
    from_port        = 8501
    to_port          = 8501
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }

  egress {
    description      = "Allow all outbound"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }
}

resource "aws_instance" "scraper" {
  ami           = "ami-0aeb7c931a5a61206"
  instance_type = "t2.micro"
  key_name      = aws_key_pair.deployer.key_name
  security_groups = [aws_security_group.allow_ssh_streamlit.name]

    user_data = <<-EOF
              #!/bin/bash
              apt update -y
              apt install -y python3-pip python3-venv unzip wget git

              wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
              dpkg -i google-chrome-stable_current_amd64.deb || apt install -f -y

              cd /home/ubuntu
              git clone https://github.com/dsanchezchu/horarios-webscraper.git
              cd horarios-webscraper

              python3 -m venv venv
              source venv/bin/activate

              pip install --upgrade pip
              pip install -r requirements.txt

              EOF

  tags = {
    Name = "scraper-instance"
  }
}

output "scraper_public_ip" {
  value = aws_instance.scraper.public_ip
  description = "La IP pública de la instancia EC2"
}