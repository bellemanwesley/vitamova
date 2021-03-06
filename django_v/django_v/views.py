from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.http import HttpResponse 
import datetime
import os
import sys
import requests
from random import randint
import hashlib
from random import shuffle

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(BASE_DIR,"django_v/"))
import authentication

sys.path.insert(1, os.path.join(BASE_DIR,"scripts/"))
import database as db
import ukrainian

class user_data_c:
    def __init__(self,email):
        self.email = email
    def get(self):
        return db.retrieve("userdata",self.email)
    def put(self,data):
        return db.send("userdata",self.email,data)
    def delete(self):
        return db.delete("userdata")

def logged_in_header():
    with open(os.path.join(BASE_DIR,"templates/sub_templates/logged_in_header.html"),"r") as f:
        return f.read()

def not_logged_in_header():
    with open(os.path.join(BASE_DIR,"templates/sub_templates/not_logged_in_header.html"),"r") as f:
        return f.read()

def home(request):
    return HttpResponseRedirect("/dashboard")

def dashboard(request):
    if request.method == "GET":
        return render(request,'authenticator.html',{"url":"/dashboard/"})
    elif request.method == "POST":
        logged_in = authentication.check_login(request)
        if logged_in == 2:
            return HttpResponseRedirect("/signup")
        if logged_in == 1:
            return HttpResponseRedirect("/login")
        if logged_in == 0:
            login_email = request.POST['email']
            user_data = user_data_c(login_email).get()
            history = user_data["history"]
            start_date = user_data["start_date"].split("-")
            date_delta = (datetime.date.today() - datetime.date(int(start_date[0]),int(start_date[1]),int(start_date[2]))).days
            if len(history) < date_delta+1:
                history += [0] * (date_delta+1-len(history))
                user_data_c(login_email).put(user_data)
            if len(history) < 7:
                week_score = "0"
            else:
                week_points = sum(history[len(history)-7:len(history)])/7
                better_than = len(list(filter(lambda x: x<week_points,history)))
                week_score = str((100.0*better_than)//len(history))
            if len(history) < 30:
                month_score = "0"
            else:
                month_points = sum(history[len(history)-30:len(history)])/30
                better_than = len(list(filter(lambda x: x<month_points,history)))
                month_score = str((100.0*better_than)//len(history))
            day_points = history[len(history)-1]
            better_than = len(list(filter(lambda x: x<day_points,history)))
            day_score = str((100.0*better_than)//len(history))
            data = {
                "day_score":day_score,
                "week_score":week_score,
                "month_score":month_score,
                "header":logged_in_header(),
                "points":user_data["points"]
            }
            return(render(request,'dashboard.html',data))

def read(request):
    if request.method == "GET":
        return render(request,'authenticator.html',{"url":"/read/"})
    elif request.method == "POST":
        logged_in = authentication.check_login(request)
        if logged_in == 2:
            return HttpResponseRedirect("/signup")
        if logged_in == 1:
            return HttpResponseRedirect("/login")
        if logged_in == 0:
            if "request" not in request.POST:
                login_email = request.POST["email"]
                user_data = user_data_c(login_email).get()
                if "read" not in user_data:
                    user_data.update({"read":{"level":"0"}})
                    user_data_c(login_email).put(user_data)
                article_number = randint(0,100)
                article = requests.get("https://wkbvitamova.s3.us-east-2.amazonaws.com/articles/"+str(article_number)+".html")
                read_content = article.text
                read_content = ukrainian.add_translate_tags(read_content)
                read_content_l = str(len(ukrainian.split_word_list(read_content)))
                read_content = "<p>" + read_content + "</p>"
                #re.sub(r'\s{2}','пута',read_content)
                read_content = read_content.replace("\n","</p><p>")
                return render(request,"read.html",{ "read_text":read_content, "word_count":read_content_l,"header":logged_in_header()})
            elif request.POST["request"] == "translate":
                word = request.POST["word"]
                translation = ukrainian.translate(word)
                return HttpResponse(translation, content_type="text/plain")
            elif request.POST["request"] == "complete":
                login_email = request.POST["email"]
                wordcount = int(request.POST["wordcount"])
                user_data = user_data_c(login_email).get()
                user_data['read']['articles'] += 1
                user_data['points'] += wordcount
                user_data['history'][len(user_data['history'])-1] += wordcount
                user_data_c(login_email).put(user_data)
                return HttpResponse("success", content_type="text/plain")
                

def flashcards(request):
    if request.method == "GET":
        return render(request,'authenticator.html',{"url":"/flashcards/"})
    elif request.method == "POST":
        logged_in = authentication.check_login(request)
        if logged_in == 2:
            return HttpResponseRedirect("/signup")
        if logged_in == 1:
            return HttpResponseRedirect("/login")
        if logged_in == 0:
            return render(request,'flashcards.html',{"header":logged_in_header()})


def transcribe(request):
    if request.method == "GET":
        return render(request,'authenticator.html',{"url":"/transcribe/"})
    elif request.method == "POST":
        if 'request' not in request.POST:
            logged_in = authentication.check_login(request)
            if logged_in == 2:
                return HttpResponseRedirect("/signup")
            if logged_in == 1:
                return HttpResponseRedirect("/login")
            if logged_in == 0:
                login_email = request.POST["email"]
                user_data = user_data_c(login_email).get()
                if "transcribe" not in user_data:
                    user_data.update({"transcribe":{"level":"0"}})
                    user_data_c(login_email).put(user_data)
                transcribe_level = int(user_data["transcribe"]["level"])
                s3 = boto3.resource('s3')
                object = s3.Object('wkbvitamova','transcribe/transcribe_embed.txt')
                transcribe_srcs = object.get()['Body'].read().decode("utf-8").split("\n")
                transcribe_src = transcribe_srcs[transcribe_level]
                object = s3.Object('wkbvitamova',"transcribe/transcribe_text_"+str(transcribe_level)+".txt")
                transcription_content = object.get()['Body'].read().decode("utf-8")
                transcription_content_l = transcription_content.split(" ")
                for i in range(len(transcription_content_l)):
                    word_bytes = bytes(transcription_content_l[i],encoding="utf-8")
                    transcription_content_l[i] = hashlib.sha256(word_bytes).hexdigest()
                transcription_content = " ".join(transcription_content_l)
                return(render(request,"transcribe.html",{"transcribe_src":transcribe_src, "video_content":transcription_content,"header":logged_in_header()}))

def accent(request):
    if request.method == "GET":
        return render(request,'authenticator.html',{"url":"/accent/"})
    elif request.method == "POST":
        if "request" not in request.POST:
            logged_in = authentication.check_login(request)
            if logged_in != 0:
                return render(request,'accent.html',{"header":not_logged_in_header()})
            if logged_in == 0:
                return render(request,'accent.html',{"header":logged_in_header()})
        else:
            if request.POST["request"] == "emphasis":
                text = request.POST["text"]
                response = ukrainian.replace_with_emphases(text)
                return HttpResponse(response, content_type="text/plain")
    
def typing(request):
    if request.method == "GET":
        return render(request,'authenticator.html',{"url":"/typing/"})
    elif request.method == "POST":
        logged_in = authentication.check_login(request)
        if logged_in == 2:
            return HttpResponseRedirect("/signup")
        if logged_in == 1:
            return HttpResponseRedirect("/login")
        if logged_in == 0:
            login_email = request.POST["email"]
            if 'request' not in request.POST:
                user_data = user_data_c(login_email).get()
                level = user_data['typing']['level']
                return render(request,'typing.html',{"header":logged_in_header(),"level":level})
            else:
                if request.POST['request'] == 'wlu':
                    article_number = randint(0,100)
                    article = requests.get("https://wkbvitamova.s3.us-east-2.amazonaws.com/articles/"+str(article_number)+".html")
                    article_content = article.text
                    response_l = ukrainian.split_word_list(article_content)
                    shuffle(response_l)
                    response = "|".join(response_l[0:20])
                    return HttpResponse(response, content_type="text/plain")
                elif request.POST["request"] == "levelup":
                    user_data = user_data_c(login_email).get()
                    user_data['typing']['level'] = str(int(user_data['typing']['level'])+1)
                    user_data['points'] += 50
                    user_data['history'][len(user_data['history'])-1] += 50
                    user_data_c(login_email).put(user_data)
                    return HttpResponse("success", content_type="text/plain")