import os

def SpeakToFile(text, target):
    file = open("speech.txt", "w")
    file.write(text.encode('UTF-8'))
    file.close()
    
    os.system("say -f speech.txt -o speech_output.aiff")
    os.system("rm speech.txt")
    
    os.system("sox speech_output.aiff padded_output.aiff pad 0.25 0.25")
    os.system("sox padded_output.aiff -c 2 stereo_output.aiff")
    os.system("lame -m j -b 160 --resample 44.1 stereo_output.aiff %s"%target)
    os.system("rm speech_output.aiff")
    os.system("rm padded_output.aiff")
    os.system("rm stereo_output.aiff")