from flask import * 
from flask import Flask,flash, session, render_template, request, redirect
from flask_mysqldb import MySQL
from tensorflow import keras
from tensorflow.keras.utils import load_img
from tensorflow.keras.preprocessing import image
import numpy as np
from flask_mail import Mail, Message
import pickle
import os

app = Flask(__name__) 
app.secret_key = b'_5#A2L"F7T8z\n\xec]/'


app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'healthcaresquad9@gmail.com'
app.config['MAIL_PASSWORD'] = 'Aish&Ana2022'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'lung' 



model = keras.models.load_model('model3.h5')
model1 = keras.models.load_model('model2.h5')



mysql = MySQL(app)

@app.route('/')
def index():
    session['loginSts']=False
    if(session['loginSts']==False):
        return render_template('index.html')

@app.route('/register')
def register():
    return render_template('register.html')

  
@app.route('/registeruser', methods = ['POST'])
def registerUser():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT email from user ''')
    emailL= cursor.fetchall()
    #print(emailL)
    for t in emailL:
        #print(t[0])
        if(t[0]==email):
            return render_template('register.html', msg="email already registered. Please login")
    else:
        cursor.execute(''' INSERT INTO user VALUES(%s,%s,%s)''',(name,email,password))
        mysql.connection.commit()
        cursor.close()
        flash("Registration Sucessfull !")
        return redirect(url_for('login'))


@app.route('/login')
def login():
    return redirect(url_for('index', _anchor="appointment"))

  
@app.route('/loginuser',methods = ['GET','POST'])  
def loginuser():
    #global loginSts
    email=request.form['email']
    password=request.form['password']

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT email, password from user ''')
    epL= cursor.fetchall()
    #print(epL)
    for t in epL:
        #print(t[0])
        if(t[0]==email and t[1]==password):
            cursor.close()
            session['email']=email
            session['loginSts']=True
            return redirect(url_for('portal'))
    else:
        flash("Invalid Credentials")
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session['loginSts']=False
    return redirect(url_for('index'))

@app.route('/forgetpass')
def forgetpass():
    return render_template('forgetpass.html',msg_txt='')


@app.route("/forgetpassemail",  methods = ['POST'])
def forgetpassemail():
    email = request.form['email']
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * from user ''')
    emailL= cursor.fetchall()
    #print(emailL)
    for t in emailL:
        #print(t[1])
        if(t[1]==email):
            msg = Message('Hello Fighter !', sender =  'healthcaresquad9@gmail.com', recipients = [email])
            msg.body = "Hey "+t[0] +", your password is - "+ t[2]
            mail.send(msg)
            return render_template('forgetpass.html', msg_txt="email sent") 
    else:
        return render_template('forgetpass.html', msg_txt="enter registerd email id") 

@app.route('/portal')
def portal():
    if(session['loginSts']==True):
        return render_template('portal.html',prediction_text='')
    else:
        return redirect(url_for('index'))

@app.route('/uploadimg', methods = ['POST'])
def uploadimg():
    if(session['loginSts']==True):
        email=session['email']
        #session['loginSts']=True
        destination_path=""
        fileobj = request.files['file']
        file_extensions =  ["JPG","JPEG","PNG"]
        uploaded_file_extension = fileobj.filename.rsplit(".",1)[1]
            #validating file extension
        if(uploaded_file_extension.upper() in file_extensions):
            destination_path= f"data/test/{fileobj.filename}"
            fileobj.save(destination_path)
            try:
                cursor = mysql.connection.cursor()
                #inserting data into table image
                cursor.execute(''' SELECT email from image WHERE email = %s''',(email,))
                record=cursor.fetchone()
                if(record == None ):
                    cursor.execute(''' INSERT INTO image (email,image) VALUES(%s,%s)''',(email,fileobj))
                    mysql.connection.commit()
                else:
                    cursor.execute(''' UPDATE image SET image = %s WHERE email= %s''',(fileobj,email))
                    mysql.connection.commit()
                
                flash('Image successfully uploaded')

                output= predictClass(destination_path)
                # per=percen(destination_path)

                if(output=="detected"):
                    if not(os.path.exists(f"data/test/infected/{fileobj.filename}")):
                        os.rename(destination_path,f"data/test/infected/{fileobj.filename}")
                else:
                    if not(os.path.exists(f"data/test/notinfected/{fileobj.filename}")):
                        os.rename(destination_path,f"data/test/notinfected/{fileobj.filename}")

                #print(output)
                #print("predicion done ************")
                
                cursor.close()
                return render_template('portal.html', prediction_text='Lung - {} '.format(output))
                #return redirect(url_for('portal'))
            except Exception as error:
                #using flash function of flask to flash errors.
                flash(f"{error}")
                return redirect(url_for('portal'))
        else:
            flash("Only images are accepted (png, jpg, jpeg, gif)")
            return redirect(url_for('portal')) 
    else:
        return redirect(url_for('index'))

def get_img_array(img_path):
  path = img_path
  img = image.load_img(path, target_size=(64,64,3))
  img = image.img_to_array(img)/255
  img = np.expand_dims(img , axis= 0 )
  
  return img


class_type = {0:'lung Adenocarcinomas', 1:'Benign Lung Tissue', 2:'Lung Squamous Cell Carcinomas'}
def image_prediction_and_visualization(path,last_conv_layer_name = "block5_conv3", model = model):
    
    img = get_img_array(path)
    res = class_type[np.argmax(model.predict(img))]
    print(f"The given X-Ray image is of type = {res}")
    print()
    print(f"The chances of image being lung Adenocarcinomas is : {model.predict(img)[0][0]*100} %")
    print(f"The chances of image being Benign Lung Tissue is : {model.predict(img)[0][1]*100} %")
    print(f"The chances of image being Lung Squamous Cell Carcinomas is : {model.predict(img)[0][2]*100} %")

def predictClass(destination_path):
    prediction = image_prediction_and_visualization(destination_path)

 
############################################################################################

# @app.route('/predict_api',methods=['POST'])
# def predict_api():
#     '''
#     For direct API calls trought request
#     '''
#     data = request.get_json(force=True)
#     prediction = model.predict([np.array(list(data.values()))])

#     output = prediction[0]
#     return jsonify(output)


if __name__ == '__main__':
    app.run(debug = True) 