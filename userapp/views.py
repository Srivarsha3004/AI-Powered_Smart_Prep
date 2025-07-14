from django.shortcuts import render, redirect , get_object_or_404
from django.contrib import messages
from userapp.models import *
import random
import urllib.parse, urllib.request, ssl
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
import urllib.request
import urllib.parse
from django.contrib.auth import logout
from django.core.mail import send_mail
import os
import random
from django.conf import settings
from userapp.models import *
from django.core.files.storage import default_storage



def generate_otp(length=4):
    otp = "".join(random.choices("0123456789", k=length))
    return otp


def user_logout(request):
    logout(request)
    messages.info(request, "Logout Successfully ")
    return redirect("user_login")

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

def index(request):
    
    feedbacks = Feedback.objects.all().order_by('-submitted_at')
    return render(request, 'index.html', {'feedbacks': feedbacks})


def about(request):
    return render(request,'about.html')



def admin(request):
    return render(request,'admin.html')



def contact(request):
    return render(request,'contact.html')



def user_register(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password') 
        phone_number = request.POST.get('phone_number')
        age = request.POST.get('age')
        address = request.POST.get('address')
        photo = request.FILES.get('photo')
        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('user_register') 
        user = User(
            full_name=full_name,
            email=email,
            password=password, 
            phone_number=phone_number,
            age=age,
            address=address,
            photo=photo
        )
        otp = generate_otp()
        user.otp = otp
        user.save()
        subject = "OTP Verification for Account Activation"
        message = f"Hello {full_name},\n\nYour OTP for account activation is: {otp}\n\nIf you did not request this OTP, please ignore this email."
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [email]
        request.session["id_for_otp_verification_user"] = user.pk
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        messages.success(request, "Otp is sent your mail !")
        return redirect("user_otp")
    return render(request,"user-register.html")



def user_otp(request):
    otp_user_id = request.session.get("id_for_otp_verification_user")
    if not otp_user_id:
        messages.error(request, "No OTP session found. Please try again.")
        return redirect("user_register")
    if request.method == "POST":
        entered_otp = "".join(
            [
                request.POST["first"],
                request.POST["second"],
                request.POST["third"],
                request.POST["fourth"],
            ]
        )
        try:
            user = User.objects.get(id=otp_user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found. Please try again.")
            return redirect("user_register")
        if user.otp == entered_otp:
            user.otp_status = "Verified"
            user.save()
            messages.success(request, "OTP verification successful!")
            return redirect("user_login")
        else:
            messages.error(request, "Incorrect OTP. Please try again.")
            return redirect("user_otp")
    return render(request,"user-otp.html")



def user_login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        try:
            user = User.objects.get(email=email)
            if user.password != password:
                messages.error(request, "Incorrect password.")
                return redirect("user_login")
            if user.status == "Accepted":
                if user.otp_status == "Verified":
                    request.session["user_id_after_login"] = user.pk
                    messages.success(request, "Login successful!")
                    return redirect("user_dashboard")
                else:
                    new_otp = generate_otp()
                    user.otp = new_otp
                    user.otp_status = "Not Verified"
                    user.save()
                    subject = "New OTP for Verification"
                    message = f"Your new OTP for verification is: {new_otp}"
                    from_email = settings.EMAIL_HOST_USER
                    recipient_list = [user.email]
                    send_mail(
                        subject, message, from_email, recipient_list, fail_silently=False
                    )
                    messages.warning(
                        request,
                        "OTP not verified. A new OTP has been sent to your email and phone.",
                    )
                    request.session["id_for_otp_verification_user"] = user.pk
                    return redirect("user_otp")
            else:
                messages.success(request, "Your Account is Not Accepted by Admin Yet")
                return redirect("user_login")
        except User.DoesNotExist:
            messages.error(request, "No User Found.")
            return redirect("user_login")
    return render(request,"user-login.html")




def user_dashboard(request):
    return render(request,"user_dashboard.html")

import os
import re
import requests
from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import render
from rapidfuzz import fuzz

def extract_text_from_pdf(pdf_path):
    extracted_text = ""
    with default_storage.open(pdf_path, "rb") as f:
        import PyPDF2
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            extracted_text += page.extract_text() or ""
    return extracted_text

def call_perplexity_api(prompt, system_content):
    headers = {
        "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        json={
            "model": "sonar",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
        },
        headers=headers
    )
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    return None

def group_similar_questions(questions, threshold=85):
    clusters = []
    for q in questions:
        matched = False
        for cluster in clusters:
            if fuzz.ratio(q.lower(), cluster[0].lower()) >= threshold:
                cluster.append(q)
                matched = True
                break
        if not matched:
            clusters.append([q])
    return clusters

def extract_questions_from_text(text):
    lines = text.splitlines()
    questions = []
    for line in lines:
        line = line.strip()
        if line.endswith('?'):
            line = re.sub(r'^[^A-Za-z]+', '', line)
            if line and line not in questions:
                questions.append(line)
    return questions

def pdf(request):
    similar_questions = {}
    pdf_paths = []
    extracted_questions_per_pdf = {}

    if request.method == "POST":
        if request.FILES.getlist("pdf_file"):
            all_text = ""
            uploaded_files = request.FILES.getlist("pdf_file")

            for pdf_file in uploaded_files:
                saved_path = default_storage.save("pdfs/" + pdf_file.name, pdf_file)
                full_url = os.path.join(settings.MEDIA_URL, saved_path)
                pdf_paths.append(full_url)

                pdf_text = extract_text_from_pdf(saved_path)
                all_text += pdf_text + "\n\n"

                questions = extract_questions_from_text(pdf_text)
                extracted_questions_per_pdf[pdf_file.name] = questions

            request.session["pdf_paths"] = pdf_paths
            request.session["pdf_text"] = all_text
            request.session["extracted_questions_per_pdf"] = extracted_questions_per_pdf

        elif "get_similar" in request.POST:
            pdf_paths = request.session.get("pdf_paths", [])
            all_text = request.session.get("pdf_text", "")
            extracted_questions_per_pdf = request.session.get("extracted_questions_per_pdf", {})

            if all_text:
                prompt = (
                    "I will give you text from several exam papers. "
                    "Return questions that appear more than once, including similar meaning or paraphrased questions, "
                    "each on its own line, ending with a question mark, no numbering or bullets.\n\n"
                    + all_text
                )
                system_content = (
                    "You are an assistant specialized in detecting repeated or similar exam questions. "
                    "Respond only with question sentences that occur in at least two papers, including paraphrases."
                )

                content = call_perplexity_api(prompt, system_content) or ""
                lines = content.splitlines()
                cleaned = []

                for line in lines:
                    line = line.strip()
                    if not line.endswith('?'):
                        continue
                    line = re.sub(r'^[^A-Za-z]+', '', line)
                    if line and line not in cleaned:
                        cleaned.append(line)

                clusters = group_similar_questions(cleaned, threshold=85)

                all_text_lower = all_text.lower()
                question_counts = {}

                for cluster in clusters:
                    total_count = 0
                    for question in cluster:
                        total_count += all_text_lower.count(question.lower())

                    if total_count > 1:
                        rep_q = cluster[0]
                        question_counts[rep_q] = total_count

                similar_questions = question_counts

    return render(request, "pdf.html", {
        "pdf_paths": pdf_paths,
        "similar_questions": similar_questions,
        "extracted_questions_per_pdf": extracted_questions_per_pdf
    })


import requests
import json
import re




def call_perplexity_api(prompt, system_content):
    headers = {
        "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        json={
            "model": "sonar",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
        },
        headers=headers
    )
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return None


from django.utils.datastructures import MultiValueDictKeyError

def user_profile(request):
    user_id  = request.session.get('user_id_after_login')
    print(user_id)
    user = User.objects.get(pk= user_id)
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        try:
            profile = request.FILES['profile']
            user.photo = profile
        except MultiValueDictKeyError:
            profile = user.photo
        password = request.POST.get('password')
        location = request.POST.get('location')
        user.user_name = name
        user.email = email
        user.phone_number = phone
        user.password = password
        user.address = location
        user.save()
        messages.success(request , 'updated succesfully!')
        return redirect('user_profile')
    return render(request,'user-profile.html',{'user':user})




# from io import TextIOWrapper
# import pickle
# import joblib
# from transformers import AlbertTokenizer
# from tensorflow.keras.models import model_from_json
# from tensorflow.keras.preprocessing.sequence import pad_sequences
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib import messages
from .models import Feedback, User


# print("Loading tokenizer...")
# loaded_tokenizer = AlbertTokenizer.from_pretrained('amazone review/albert_tokenizer')


# print("Loading label encoder...")
# label_encoder = joblib.load('amazone review/label_encoder.joblib')


# print("Loading model architecture...")
# model_architecture_path = 'amazone review/bylstm_model_architecture.json'
# with open(model_architecture_path, 'r') as json_file:
#     loaded_model_json = json_file.read()


# print("Loading model weights...")
# model_weights_path = 'amazone review/bylstm_model_weights.h5'
# loaded_model = model_from_json(loaded_model_json)
# loaded_model.load_weights(model_weights_path)

# max_len = 256


# def predict_sentiment(text):
#     print(f"Predicting sentiment for text: {text}")

    
#     print(f"Tokenizing and padding input text...")
#     sequences = [loaded_tokenizer.encode(text, max_length=max_len, truncation=True, padding='max_length')]
#     padded_sequences = pad_sequences(sequences, maxlen=max_len, padding='post', truncating='post')

    
#     print(f"Making prediction using the model...")
#     predictions = loaded_model.predict(padded_sequences)
#     print(f"Model prediction output: {predictions}")

    
#     predicted_label = label_encoder.inverse_transform(predictions.argmax(axis=1))[0]
#     print(f"Predicted sentiment label: {predicted_label}")
    
    
#     return predicted_label


def feedback(request):
    user_id = request.session.get('user_id_after_login')
    print(f"User ID from session: {user_id}")

    if request.method == 'POST':
        print(f"Processing POST request...")
        
        user = get_object_or_404(User, pk=user_id)

      
        user_name = request.POST.get('user_name')
        user_email = request.POST.get('user_email')
        rating = request.POST.get('rating')
        additional_comments = request.POST.get('additional_comments')

        print(f"Feedback form data: user_name={user_name}, user_email={user_email}, rating={rating}, additional_comments={additional_comments}")

        
        print(f"Performing sentiment analysis...")
        # sentiment = predict_sentiment(additional_comments)  
        # print(f"Predicted sentiment: {sentiment}")

        
        
        # if sentiment == 1:
        #     sentiment_label = "neutral"
        # elif sentiment == 2:
        #     sentiment_label = "positive"
        # else:
        #     sentiment_label = "negative"
        
        # print(f"Mapped sentiment label: {sentiment_label}")

        
        print(f"Saving feedback to the database...")
        feedback = Feedback.objects.create(
            user=user,
            user_name=user_name,
            user_email=user_email,
            rating=rating,
            additional_comments=additional_comments,
            sentiment=None  
        )
        print(f"Feedback saved: {feedback}")

        
        messages.success(request, "Your feedback has been submitted successfully.")
        return redirect('feedback')

    print("Returning feedback page...")
    return render(request, "user-feedback.html")





import re
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from .models import Conversation
from django.views.decorators.csrf import csrf_exempt

import re
import json
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Conversation
from django.views.decorators.csrf import csrf_exempt
from googletrans import Translator


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests

# userapp/views.py
from django.http import JsonResponse
from googletrans import Translator

# userapp/views.py
from django.http import JsonResponse
from googletrans import Translator, LANGUAGES








import re
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from .models import Conversation
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def user_chatbot(request):
    conversations = Conversation.objects.all().order_by('created_at')

    if request.method == 'POST':
        if 'translate_text' in request.POST:
            original_text = request.POST.get('translate_text')
            target_lang = request.POST.get('language')

            try:
                translation_response = requests.post(
                    'https://libretranslate.de/translate',
                    headers={'Content-Type': 'application/json'},
                    json={
                        'q': original_text,
                        'source': 'auto',
                        'target': target_lang,
                        'format': 'text'
                    }
                )

                translated_text = translation_response.json().get('translatedText', 'Translation failed.')
            except Exception as e:
                translated_text = 'Translation error.'

            return render(request, 'chatbot.html', {
                'conversations': conversations,
                'translated_text': translated_text
            })

        user_message = request.POST.get('message', '').strip()
        if user_message:
            headers = {
                "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "Be precise and concise."},
                    {"role": "user", "content": user_message}
                ]
            }

            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                json=payload,
                headers=headers
            )

            bot_response = "Error: Could not get response from AI"
            if response.status_code == 200:
                try:
                    bot_response = response.json()['choices'][0]['message']['content']
                    bot_response = re.sub(r'\*\*(.*?)\*\*', r'\1', bot_response)
                    bot_response = re.sub(r'\*(.*?)\*', r'\1', bot_response)
                    bot_response = re.sub(r'\[\d+\]', '', bot_response)
                except Exception:
                    bot_response = "An error occurred while processing the response."

            Conversation.objects.create(
                user_message=user_message,
                bot_response=bot_response
            )
            return redirect('chatbot')

    return render(request, 'chatbot.html', {'conversations': conversations})
