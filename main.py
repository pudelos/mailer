from decouple import config
import smtplib
from pyfiglet import Figlet
from termcolor import colored
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
from os.path import exists
import json
import re
import ssl


def create_schema(filename):
  try:
    example_schema = json.load(open('sample.json'))
  except FileNotFoundError:
    error('"sample.json" file is missing', 1)
  except json.decoder.JSONDecodeError:
    error('"sample.json" file is incorrect', 1)

  with open(filename, 'w') as outfile:
    json.dump(example_schema, outfile, indent=2)
  
  exit(colored('Update ' + filename + ' file and run program again', 'green'))


def error(msg, stop=0):
  print(colored("error: " + msg, 'red'))
  if stop:
    exit()


def send(data, CONFIG):
  try:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(CONFIG["smtp"], CONFIG["port"], context=context) as server:
      server.login(CONFIG["login"], CONFIG["password"])

      length = len(data)
      with Progress() as progress:
        task = progress.add_task("[green]Sending...", total=length)
        for i, email in enumerate(data):
          message = 'Subject: {}\n\n{}'.format(email["title"], email["body"])
          server.sendmail(CONFIG["login"], email["to"], message)
          progress.update(task, advance=1/length*length)
  except:
    error('wrong configuration. Check .env account data', 1)


def check_file(filename):
  if not exists(filename):
    error('file does not exist')
    if Confirm.ask("Create a " + filename + " file with sample data?", default="y"):
      create_schema(filename)
    else:
      exit()


def update_string(old_str, user, indexes):
  invalids = []
  end = 0
  lastIndex = -1
  actual_text = ''
  for (start, end) in indexes:
    name = old_str[start+2:end-1]
    if user.get(name) is None:
      if name not in invalids:
        invalids.append(name)
      continue
        
    actual_text += old_str[lastIndex+1:start] + user[name]
    lastIndex += end
  actual_text += old_str[end:]

  return {
    "text": actual_text,
    "invalids": invalids
  }


def convert_json(filename):
  try:
    file = open('data.json')
    data = json.load(file)

    invalids = []
    completed_data = []

    title = data["structure"]["title"]
    body = data["structure"]["body"]
    title_indexes = [(m.start(0), m.end(0)) for m in re.finditer('\${(.+?)}', title)]
    body_indexes = [(m.start(0), m.end(0)) for m in re.finditer('\${(.+?)}', body)]

    for user in data["users"]:
      title_data = update_string(title, user, title_indexes)
      invalids += title_data["invalids"]

      body_data = update_string(body, user, body_indexes)
      invalids += body_data["invalids"]

      completed_data.append({
        "to": user["emails"],
        "title": title_data["text"],
        "body": body_data["text"]
      })
    
    if invalids:
      error_value = filename + " file data is invalid. Make sure "
      for name in invalids:
        error_value += '"' + name + '", '
      
      error_value = error_value[0:-2]
      error_value += " users variable exist."
      error(error_value, 1)

    return completed_data 
  except ValueError:
    error(filename + ' file content is incorrect', 1) 


def main():
  print(colored(Figlet(font='banner3-D').renderText('Mailer'), 'green'))
  
  try:
    CONFIG = {
      'smtp': config('SMTP', default='smtp.gmail.com'),
      'port': config('PORT', default=465),
      'login': config('LOGIN'),
      'password': config('PASSWORD')
    }
  except:
    error('update and rename ".env_example" file to ".env"', 1)

  if not CONFIG["login"] or not CONFIG["password"]:
    error('check account data in .env file', 1)

  filename = Prompt.ask("Enter filename", default="data.json")
  check_file(filename)
  converted_json = convert_json(filename)
  send(converted_json, CONFIG)


main()