import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from oauthlib.oauth2 import WebApplicationClient
import openai
import requests
from textblob import TextBlob  # Sentiment analysis for mood detection
from transformers import pipeline