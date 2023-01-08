import tweepy
import pandas as pd
import re
from textblob import TextBlob
import nltk
nltk.download('vader_lexicon')
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import numpy as np
from PIL import Image
import wordcloud
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from flask import Flask
from flask import session, render_template, request
import base64 
import io
from io import BytesIO

app = Flask(__name__)
app.secret_key = "manbearpig_MUDMAN888"

#First page when providing tokens is required
@app.route('/', methods=['POST', 'GET'])
def sign_up():

    return render_template("sign-up.html")

#Directs to the page where we can set up searching querry. If there is error with tokens, redirecting to the error page.
@app.route("/home", methods=['POST', 'GET'])
def home():
    #testing querry, if error then returns error page, if no error then pass you to the query page
    session['api_key']=request.form['api_key']
    session['api_key_secret']=request.form['api_key_secret']
    session['access_token']=request.form['access_token']
    session['access_token_secret']=request.form['access_token_secret']
    api_key=session.get('api_key')
    api_key_secret=session.get('api_key_secret')
    access_token=session.get('access_token')
    access_token_secret=session.get('access_token_secret')
    authenticator = tweepy.OAuthHandler(api_key, api_key_secret)
    authenticator.set_access_token(access_token, access_token_secret)   
    while True:
        try:
            test_query = "test -filter:retweets"
            api = tweepy.API(authenticator, wait_on_rate_limit=True)
            tweet_cursor_test = tweepy.Cursor(api.search_tweets, q=test_query, lang="pl",
            result_type="mixed").items(1)
            tweets_test = [tweet for tweet in tweet_cursor_test]
        except:
            print("Oops!  That was no valid number.  Try again...")
            return render_template("error.html")
        else:
            print("loged in")
            break
    #end of testing query
    return render_template("index.html")

#Returns us to the home page without testing login details again.
@app.route("/nextquerry", methods=['POST', 'GET'])
def nextquerry():
    return render_template("index.html")

#Logging into twitter API, scrapping tweets, preprocessing them, creating sentiment chart and word cloud.
@app.route("/sentiment", methods=['POST', 'GET'])
def submit():


   
    #get tokens + keys
    api_key=session.get('api_key')
    api_key_secret=session.get('api_key_secret')
    access_token=session.get('access_token')
    access_token_secret=session.get('access_token_secret')
    #set up authentication
    authenticator = tweepy.OAuthHandler(api_key, api_key_secret)
    authenticator.set_access_token(access_token, access_token_secret)
    #seting up query and scrapping tweets
    tweets_amount=int(request.form['tweets_amount'])
    language=str(request.form['language'])
    x=str(request.form['question'])
    query = f"{x} -filter:retweets"
    api = tweepy.API(authenticator, wait_on_rate_limit=True)
    tweet_cursor = tweepy.Cursor(api.search_tweets, q=query, lang=language,
    result_type="mixed").items(tweets_amount)
    tweets = [tweet for tweet in tweet_cursor]
    # create dataframe with tweet text only
    columns = ['text']
    data = []
    for tweet in tweets:
        data.append([tweet.text])
    tweet_list_df = pd.DataFrame(data, columns=columns)
    tweet_list_df = tweet_list_df.replace(r'\n',' ', regex=True) #removing line breaks



    #preprocessing tweets (cleaning text)
    def preprocess_tweet(sen):
        #Cleans text data up 
        sentence = sen.lower()
        # Remove RT
        sentence = re.sub('RT @\w+: ', " ", sentence)
        # Remove special characters (excluding polish letters)
        sentence = re.sub("(@[A-Za-z0-9-AaĄąBbCcĆćDdEeĘęFfGgHhIiJjKkLlŁłMmNnŃńOoÓóPpRrSsŚśTtUuWwYyZzŹźŻż]+)|([^0-9A-Za-zAaĄąBbCcĆćDdEeĘęFfGgHhIiJjKkLlŁłMmNnŃńOoÓóPpRrSsŚśTtUuWwYyZzŹźŻż \t])|(\w+:\/\/\S+)", " ", sentence)   
        # Single character removal and leaving words longer than 3 
        sentence = re.sub(r"\s+[a-zA-Z]\s+", ' ',sentence)  
        # When we remove apostrophe from the word "Mark's", the apostrophe is replaced by an empty space. Hence, we are left with single character "s" that we are removing here.
        sentence = re.sub(r'\b\w{1,3}\b', '', sentence)
        # Remove multiple spaces
        sentence = re.sub(r'\s+', ' ',sentence)
        return sentence
    cleaned_tweets = []

    #updating df with cleaned tweets:
    success = False
    while not success:
        try:
            for t in tweet_list_df['text']:
                cleaned_tweet = preprocess_tweet(t)
                cleaned_tweets.append(cleaned_tweet)
            tweet_list_df['cleaned'] = pd.DataFrame(cleaned_tweets)
            success = True    
        except ValueError:
            print("There is no any tweet containing ")
            return render_template("error.html", error="There is no any tweet containing")
        else:
            print("tweets successfully searched")
            break
    #Calculating Negative, Positive, Neutral and Compound values

    tweet_list_df[['polarity', 'subjectivity']] = tweet_list_df['cleaned'].apply(lambda Text: pd.Series(TextBlob(Text).sentiment))
    for index, row in tweet_list_df['cleaned'].iteritems():
        score = SentimentIntensityAnalyzer().polarity_scores(row)
        neg = score['neg']
        neu = score['neu']
        pos = score['pos']
        comp = score['compound']
        if comp <= -0.05:
            tweet_list_df.loc[index, 'sentiment'] = "negative"
        elif comp >= 0.05:
            tweet_list_df.loc[index, 'sentiment'] = "positive"
        else:
            tweet_list_df.loc[index, 'sentiment'] = "neutral"
        tweet_list_df.loc[index, 'neg'] = neg
        tweet_list_df.loc[index, 'neu'] = neu
        tweet_list_df.loc[index, 'pos'] = pos
        tweet_list_df.loc[index, 'compound'] = comp

    tweet_list_df_negative = tweet_list_df[tweet_list_df["sentiment"]=="negative"]
    tweet_list_df_positive = tweet_list_df[tweet_list_df["sentiment"]=="positive"]
    tweet_list_df_neutral = tweet_list_df[tweet_list_df["sentiment"]=="neutral"]

    def count_values_in_column(data,feature):
        total=data.loc[:,feature].value_counts(dropna=False)
        percentage=round(data.loc[:,feature].value_counts(dropna=False,normalize=True)*100,2)
        return pd.concat([total,percentage],axis=1,keys=['Total','Percentage'])
    count_values_in_column(tweet_list_df,"sentiment")

    # create data for Pie Chart
    pichart = count_values_in_column(tweet_list_df,"sentiment")
    names= pichart.index
    size=pichart["Percentage"]

    # Create a circle for the center of the plot
    my_circle=plt.Circle( (0,0), 0.7, color='white')
    plt.pie(size, labels=names, colors=['green','blue','red'])
    p=plt.gcf()
    p.gca().add_artist(my_circle)

    #uploading chart into buffer:
    buf = BytesIO()
    plt.savefig(buf, format="png")
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    url=f"data:image/png;base64,{data}"
    #clearing plot before next querry
    plt.cla() 
    
    #creating word cloud
    def create_wordcloud(text,file_name):
        mask = np.array(Image.open("templates/cloud.png"))
        file_name = str(file_name)
        stopwords = set(STOPWORDS)
        wc = WordCloud(background_color="white",
                        mask = mask,
                        max_words=60,
                        stopwords=stopwords,
                        repeat=True)
        wc.generate(str(text))
        wc.to_file(f"templates/temp/{file_name}.png") 
        path=f"templates/temp/{file_name}.png"
    create_wordcloud(tweet_list_df["cleaned"].values,'all')

    #uploading word cloud into buffer
    all_buf = BytesIO()
    all_byte = Image.open("templates/temp/all.png")
    all_byte.save(all_buf, "PNG")
    data_all = base64.b64encode(all_buf.getbuffer()).decode("ascii")
    url_all=f"data:image/png;base64,{data_all}"

    return render_template("sentiment.html", plot_url=url, url_all=url_all)

if __name__ == '__main__':
    app.run(debug=True)

