# speechmatics_python
Example script (supported) to help you integrate with our API

This code was developed and tested with Python 2.7.12 and Python 3.5.2   

This is an example script for uploading audio files and saving the transcript in a .json file  

## Requirements
You will need to have the requests module installed in your Python environment.  
```
pip install requests
```

## Example usage:
```
python ./speechmatics.py -a example.mp3 -l en-US -i $user_id -k $auth_token -o example.json  
```

In this example the script uploads 'example.mp3', transcribes it using our en-US speech to text product and saves the resulting transcription as 'example.json' when the job has completed.
