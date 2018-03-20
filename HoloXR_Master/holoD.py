# Requirements:
# pip install tk
# pip install pillow

from tkinter import *
from PIL import Image
from PIL import ImageTk
import cv2, threading, os, time
from threading import Thread
from os import listdir
from os.path import isfile, join

### Function to set wich sprite must be drawn
def put_sprite(num):
    global SPRITES, BTNS
    SPRITES[num] = (1 - SPRITES[num]) #not actual value
    if SPRITES[num]:
        BTNS[num].config(relief=SUNKEN)
    else:
        BTNS[num].config(relief=RAISED)

#Draws sprite over a image
#It uses the alpha chanel to see which pixels need to be reeplaced
# Input: image, sprite: numpy arrays
# output: resulting merged image
def draw_sprite(frame, sprite, x_offset, y_offset):
    (h,w) = (sprite.shape[0], sprite.shape[1])
    (imgH,imgW) = (frame.shape[0], frame.shape[1])

    if y_offset+h >= imgH: #if sprite gets out of image in the bottom
        sprite = sprite[0:imgH-y_offset,:,:]

    if x_offset+w >= imgW: #if sprite gets out of image to the right
        sprite = sprite[:,0:imgW-x_offset,:]

    if x_offset < 0: #if sprite gets out of image to the left
        sprite = sprite[:,abs(x_offset)::,:]
        w = sprite.shape[1]
        x_offset = 0

    #for each RGB chanel
            #chanel 4 is alpha: 255 is not transpartne, 0 is transparent background
        frame[y_offset:y_offset+h, x_offset:x_offset+w, c] =  \
        sprite[:,:,c] * (sprite[:,:,3]//255.0) +  frame[y_offset:y_offset+h, x_offset:x_offset+w, c] * (1.0 - sprite[:,:,3]//255.0)
    return frame


# Returns the rectangles
# Img is a BGR image
# haar_cascade is a cv2.CascadeClassifier object
# the other inputs are the filter parameters
def apply_Haar_filter(img, haar_cascade,scaleFact = 1.05, minNeigh = 3, minSizeW = 30):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    features = haar_cascade.detectMultiScale(
        gray,
        scaleFactor=scaleFact,
        minNeighbors=minNeigh,
        minSize=(minSizeW, minSizeW),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    return features


#Adjust the given sprite to the head's width and position
#in case of the sprite not fitting the screen in the top, the sprite should be trimed
def adjust_sprite2head(sprite, head_width, head_ypos):
    (h_sprite,w_sprite) = (sprite.shape[0], sprite.shape[1])
    factor = 1.0*head_width/w_sprite
    sprite = cv2.resize(sprite, (0,0), fx=factor, fy=factor) # adjust to have the same width as head
    (h_sprite,w_sprite) = (sprite.shape[0], sprite.shape[1])
    y_orig =  head_ypos-h_sprite # adjust the position of sprite to end where the head begins
    if (y_orig < 0): #check if the head is not to close to the top of the image and the sprite would not fit in the screen
            sprite = sprite[abs(y_orig)::,:,:] #in that case, we cut the sprite
            y_orig = 0 #the sprite then begins at the top of the image
    return (sprite, y_orig)


def apply_sprite(image, path2sprite,w,x,y):
    sprite = cv2.imread(path2sprite,-1)
    (sprite, y_final) = adjust_sprite2head(sprite, w, y)
    image = draw_sprite(image,sprite,x, y_final)


def apply_sprite2feature(image, sprite_path, haar_filter, x_offset, y_offset, y_offset_image, adjust2feature, desired_width, x, y, w, h):
    sprite = cv2.imread(sprite_path,-1)
    (h_sprite,w_sprite) = (sprite.shape[0], sprite.shape[1])

    xpos = x + x_offset
    ypos = y + y_offset
    factor = 1.0*desired_width/w_sprite

    sub_img = image[y + y_offset_image:y+h,x:x+w,:]

    feature = apply_Haar_filter(sub_img, haar_filter, 1.3 , 10, 10)
    if len(feature)!=0:
        xpos, ypos = x, y + feature[0,1] #adjust only to feature in y axis (eyes)

        if adjust2feature:
            size_mustache = 1.2 #how many times bigger than mouth
            factor = 1.0*(feature[0,2]*size_mustache)/w_sprite
            xpos =  x + feature[0,0] - int(feature[0,2]*(size_mustache-1)//2) #centered respect to width
            ypos = y + y_offset_image + feature[0,1] - int(h_sprite*factor) #right on top

    sprite = cv2.resize(sprite, (0,0), fx=factor, fy=factor)
    image = draw_sprite(image,sprite,xpos,ypos)

#Principal Loop where openCV (magic) ocurs
def cvloop(run_event):
    global panelA
    global SPRITES

    dir_ = "./vectors/flyes/"
    flies = [f for f in listdir(dir_) if isfile(join(dir_, f))] #image of flies to make the "animation"
    i = 0
    video_capture = cv2.VideoCapture(0) #read from webcam
    #video_capture = cv2.flip(cap,0)
    (x,y,w,h) = (0,0,10,10) #whatever initial values

    #Filters path
    haar_faces = cv2.CascadeClassifier('./mrai/haarcascade_frontalface_default.xml')
    haar_eyes = cv2.CascadeClassifier('./mrai/haarcascade_eye.xml')
    haar_mouth = cv2.CascadeClassifier('./mrai/Mouth.xml')
    haar_nose = cv2.CascadeClassifier('./mrai/Nose.xml')
    fullbody = cv2.CascadeClassifier('./mrai/haarcascade_fullbody.xml')

    while run_event.is_set(): #while the thread is active we loop
        ret, image = video_capture.read(0)

        faces = apply_Haar_filter(image, haar_faces, 1.05 , 3, 30)
        for (x,y,w,h) in faces: #if there are faces
            #take first face found (x,y,w,h) = (faces[0,0],faces[0,1],faces[0,2],faces[0,3])

            #hat condition
            if SPRITES[0]:
                apply_sprite(image, "./vectors/hat.png",w,x,y)

            #mustache condition
            if SPRITES[1]:
                #empirically mouth is at 2/3 of the face from the top
                #empirically the width of mustache is have of face's width (offset of w/4)
                #we look for mouths only from the half of the face (to avoid false positives)
                apply_sprite2feature(image, "./vectors/mustache.png", haar_mouth, w//4, 2*h//3, h//2, True, w//2, x, y, w, h)

            #glasses condition
            if SPRITES[3]:
                #empirically eyes are at 1/3 of the face from the top
                apply_sprite2feature(image, "./vectors/glasses.png", haar_eyes, 0, h//3, 0, False, w, x, y, w, h)

            #flies condition
            if SPRITES[2]:
                #to make the "animation" we read each time a different image of that folder
                # the images are placed in the correct order to give the animation impresion
                apply_sprite(image, dir_+flies[i],w,x,y)
                i+=1
                i = 0 if i >= len(flies) else i #when done with all images of that folder, begin again
	    #Dress condition
            if SPRITES[1]:
                #empirically mouth is at 2/3 of the face from the top
                #empirically the width of mustache is have of face's width (offset of w/4)
                #we look for mouths only from the half of the face (to avoid false positives)
                apply_sprite2feature(image, "./vectors/dress.png", fullbody, w//4, 2*h//3, h//2, True, w//2, x, y, w, h)


        # OpenCV represents image as BGR; PIL but RGB, we need to change the chanel order
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # conerts to PIL format
        image = Image.fromarray(image)
        # Converts to a TK format to visualize it in the GUI
        image = ImageTk.PhotoImage(image)
        # Actualize the image in the panel to show it
        panelA.configure(image=image)
        panelA.image = image
    video_capture.release()

# Initialize GUI object
root = Tk()
root.title("HoloXR")
this_dir = os.path.dirname(os.path.realpath(__file__))
# Adds a custom logo
imgicon = PhotoImage(file=os.path.join(this_dir,'imgs/icon.gif'))
root.tk.call('wm', 'iconphoto', root._w, imgicon)

##Create 3 buttons and assign their corresponding function to active sprites
btn1 = Button(root, text="Hat", command = lambda: put_sprite(0))
btn1.pack(side="top", fill="both", expand="no", padx="10", pady="10")

btn2 = Button(root, text="Mustache", command = lambda: put_sprite(1))
btn2.pack(side="top", fill="both", expand="no", padx="10", pady="10")

btn3 = Button(root, text="Flies", command = lambda: put_sprite(2))
btn3.pack(side="top", fill="both", expand="no", padx="10", pady="10")

btn4 = Button(root, text="Glasses", command = lambda: put_sprite(3) )
btn4.pack(side="top", fill="both", expand="no", padx="10", pady="10")

btn5 = Button(root, text="Dress", command = lambda: put_sprite(4))
btn5.pack(side="top", fill="both", expand="no", padx="10", pady="10")
# Create the panel where webcam image will be shown
panelA = Label(root)
panelA.pack( padx=10, pady=10)

# Variable to control which sprite you want to visualize
SPRITES = [0,0,0,0,0] #hat, mustache, flies, glasses -> 1 is visible, 0 is not visible
BTNS = [btn1, btn2, btn3, btn4, btn5]


# Creates a thread where the magic ocurs
run_event = threading.Event()
run_event.set()
action = Thread(target=cvloop, args=(run_event,))
action.setDaemon(True)
action.start()


# Function to close all properly, aka threads and GUI
def terminate():
        global root, run_event, action
        print("visit: www.abi-ai.com")
        run_event.clear()
        time.sleep(1)
        #action.join() #strangely in Linux this thread does not terminate properly, so .join never finishes
        root.destroy()
        print("$$$$$$ Peace! $$$$$$$")
	#print("Africa Machine Intelligence Software 2018")

# When the GUI is closed it actives the terminate function
root.protocol("WM_DELETE_WINDOW", terminate)
root.mainloop() #creates loop of GUI
