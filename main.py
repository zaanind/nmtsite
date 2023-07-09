from flask import Flask, render_template, request, send_file, make_response
import re
import subprocess
import os
import pysrt
from werkzeug.utils import secure_filename



cmdfunc = os.environ['cmdfunc']




app = Flask(__name__)


# Configure the upload folder and allowed file extensions
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'srt'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/translates', methods=['POST'])
def translates():
    # Get input text from form
    input_text = request.json.get('input_text', '')

    
# Remove .,;?$! from the input text
    input_text = input_text.replace(";;", "\n")
    input_text = input_text.replace("?", " ?")
    input_text = input_text.replace("-", "")

    input_text = re.sub(r'[.,;$!]', '', input_text)

# Convert input text to lowercase
    input_text = input_text.lower()



    # Write input text to file
    with open('input.txt', 'w') as f:
        f.write(input_text)

    # Define path to model and output file
    model_path = 'model_step_15000.pt'
    output_path = 'output.txt'

    # Define NMT functions
    command = [cmdfunc,
               '-model', model_path,
               '-src', 'input.txt',
               '-output', output_path,
               '-verbose']

    # Run NMT command using subprocess
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()


    # Extract predicted lines from the output
    pattern = r"PRED (\d+): (.+)"
    predicted_lines = re.findall(pattern, error.decode())

    # Join the predicted lines into a single translation with line breaks
    translation = ""
    for line in predicted_lines:
        translation += f"PRED {line[0]}: {line[1]}\n"


    # Return translation as JSON response
    return {'input': input_text, 'translation': translation}




@app.route('/translate', methods=['POST'])
def translate():
    # Get input text from form
    input_text = request.form['input_text']
    
# Remove .,;?$! from the input text
    input_text = input_text.replace(";;", "\n")

    input_text = re.sub(r'[.,;?$!]', '', input_text)

# Convert input text to lowercase
    input_text = input_text.lower()



    # Write input text to file
    with open('input.txt', 'w') as f:
        f.write(input_text)

    # Define path to model and output file
    model_path = 'model_step_15000.pt'
    output_path = 'output.txt'

    # Define NMT functions
    command = [cmdfunc,
               '-model', model_path,
               '-src', 'input.txt',
               '-output', output_path,
               '-verbose']

    # Run NMT command using subprocess
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()

    # Read output file and extract translation
    with open(output_path, 'r') as f:
        translation = f.read().strip()
   # print(translation)

    # Return translation as JSON response
    return {'input': input_text, 'translation': translation}




@app.route('/subtools', methods=['GET', 'POST'])
def subtools():
    if request.method == 'POST':
        if 'subtitle' not in request.files:
            return 'No subtitle file selected'

        subtitle_file = request.files['subtitle']

        if subtitle_file.filename == '':
            return 'No subtitle file selected'

        if subtitle_file and allowed_file(subtitle_file.filename):
            filename = secure_filename(subtitle_file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            subtitle_file.save(upload_path)

            subtitles = pysrt.open(upload_path)

            return render_template('subtools.html', subtitles=subtitles)
        else:
            return 'Invalid file type. Only SRT files are allowed.'

    return render_template('subtools.html')



@app.route('/download', methods=['POST'])
def download():
    # Retrieve the edited subtitles from the form
    edited_subtitles = request.form.getlist('subtitle')
    edited_start_times = request.form.getlist('start_time')
    edited_end_times = request.form.getlist('end_time')

    # Generate the new SRT content
    new_srt_content = ""
    for i in range(len(edited_subtitles)):
        new_srt_content += f"{i+1}\n"
        new_srt_content += f"{edited_start_times[i]} --> {edited_end_times[i]}\n"
        new_srt_content += f"{edited_subtitles[i]}\n\n"

    # Save the new SRT content to a temporary file
    temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.srt')
    with open(temp_file_path, 'w',encoding='utf-8') as f:
        f.write(new_srt_content)

    # Perform any necessary processing on the SRT file (if needed)
    # ...

    # Set the Content-Disposition header to specify the filename
    response = send_file(temp_file_path, as_attachment=True)
    response.headers['Content-Disposition'] = 'attachment; filename=edited_subtitle.srt'

    # Remove the temporary file after sending the response
    os.remove(temp_file_path)

    return response


#if __name__ == '__main__':
  #  app.run(debug=True)


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080,threaded=True, debug=True)
