from bookcollection import app, os, db
from flask import render_template, redirect, url_for, flash, request
from bookcollection.models import Book, Review, Quote
from sqlalchemy import or_
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import base64
import io
from bs4 import BeautifulSoup
import requests
import re
from better_profanity import profanity
from textatistic import Textatistic


#nltk.download('wordnet')
#nltk.download('stopwords')
#nltk.download('punkt')

class DataCollection:
    '''
    Class is used for Retrieval and Insertion of Childrens' Books Data
    '''
    def __init__(self, book_name, author_name):
        self.title = book_name.split(", Book")[0]
        self.author = author_name
        self.url = "https://www.commonsensemedia.org"
        self.kwroute = "book-reviews"
        self.headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
                    }
        #self.firefox_driver_path = "geckodriver.exe"
        self.book_review_url = "https://www.goodreads.com"
        self.command = f"/search?utf8=✓&q={self.getAuthorFormatted()}+{self.getTitleFormatted()}&search_type=books&search[field]=on"
        self.quotes_command = "/work/quotes/"

    def getDescription(self):
        book = Book.query.filter(Book.title.like(self.title + "%")).first()
        return book.description

    def getAuthorFormatted(self):
        return self.author.lower().replace(" ", "+")

    def getTitleFormatted(self):
        return self.title.lower().replace(" ", "+")

    def getReviewText(self):
        corpus = ""
        for review in self.getReviewsFromWeb():
            corpus += review
        stop_words = stopwords.words('english')
        stop_words = stop_words + ["book", "story", "tale", "novel", "author"]
        lemmatizer = WordNetLemmatizer()
        lemmatized_words = [lemmatizer.lemmatize(word, pos='v') for word in word_tokenize(corpus.lower()) if
                            word not in stop_words and word.isalnum()]
        final_set = " ".join(lemmatized_words)
        return final_set

    def getQuoteTextRaw(self):
        # if quotes not found in DB try retrieving from web and loading into DB
        corpus = ""
        for quote in self.getQuotesFromWeb():
            corpus += quote
        return corpus

    def getQuoteText(self):
        corpus = ""
        for quote in self.getQuotesFromWeb():
            corpus += quote
        stop_words = stopwords.words('english')
        lemmatizer = WordNetLemmatizer()
        lemmatized_words = [lemmatizer.lemmatize(word, pos='v') for word in word_tokenize(corpus.lower()) if
                            word not in stop_words and word.isalnum()]
        final_set = " ".join(lemmatized_words)
        return final_set

    def getReviewsFromWeb(self):
        reviews_links_soup = self.getBookReviewSoup()
        if reviews_links_soup:
            #print("test2")
            review_divs = reviews_links_soup.findAll("div", {"id": "bookReviews"})[0]
            review_spans = review_divs.findAll('span', id=re.compile(r"reviewTextContainer\d.*"))
            for span in review_spans:
                txtContSpan = span.find("span", id=re.compile(r"freeTextContainer\d.*"))
                txtSpan = span.find("span", id=re.compile(r"freeText\d.*"))
                if txtSpan:
                    yield txtSpan.get_text().strip()
                else:
                    yield txtContSpan.get_text().strip()

    def getQuotesFromWeb(self):
        quotes_page = self.getBookQuoteSoup()
        if quotes_page:
            quotes_divs = quotes_page.findAll('div', {'class': 'quoteText'})
            #print(quotes_divs)
            for quotes in quotes_divs:
                quote_extracted = quotes.get_text().replace("\n", "").split("―")[0]
                quote_trimmed = quote_extracted.strip().lstrip("“").rstrip("”")
                yield quote_trimmed

    def getBookReviewSoup(self):
        author_links_res = requests.get(self.book_review_url + self.command)
        #print(self.book_review_url + self.command)
        author_links_soup = BeautifulSoup(author_links_res.text, features="html.parser")
        formatted_title = self.title.replace(": ", " \(")
        #print(formatted_title)
        #print(self.book_review_url + self.command)
        pattern = rf"^({formatted_title}).*"
        print(pattern)
        book_review_span = author_links_soup.find("span", text=re.compile(pattern, re.IGNORECASE))
        if book_review_span:
            book_review_parent_tag = book_review_span.find_parent()
            book_review_link = book_review_parent_tag["href"]
            print(book_review_link)
            review_links_res = requests.get(self.book_review_url + book_review_link)
            reviews_links_soup = BeautifulSoup(review_links_res.text, features="html.parser")
            return reviews_links_soup
        else:
            return None

    def getBookQuoteSoup(self):
        reviews_links_soup = self.getBookReviewSoup()
        book_quote_a_tag = reviews_links_soup.find("a", {"class": "actionLink"}, text="More quotes…")
        if book_quote_a_tag:
            book_quote_link = book_quote_a_tag["href"]
            book_quote_res = requests.get(self.book_review_url + book_quote_link)
            book_quote_soup = BeautifulSoup(book_quote_res.text, features="html.parser")
            return book_quote_soup
        else:
            return None

    def saveImage(self, review_text, file_name):
        try:
            wordcloud = WordCloud(background_color="white", width=800, height=400).generate(review_text)
            plt.figure(figsize=(10, 8))
            plt.axis("off")
            plt.imshow(wordcloud, interpolation='bilinear')
            image_path = os.path.join(app.config['IMG_DIR'], file_name + '.png')
            #        clean = Clean(directory=app.config['IMG_DIR'])
            #        clean.cleanUp()
            print(image_path)
            plt.tight_layout()
            plt.savefig(image_path, bbox_inches="tight")
            plt.close()
        except Exception as e:
            print(f"Exception: {str(e)}")

    def getWCImage(self, review_text):
        try:
            wordcloud = WordCloud(background_color="white", width=800, height=400).generate(review_text)
            plt.figure(figsize=(6, 4))
            plt.axis("off")
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.tight_layout()
            data = io.BytesIO()
            plt.savefig(data, bbox_inches="tight", format="png")
            data.seek(0)
            plt.close()
            return base64.b64encode(data.getvalue())
        except Exception as e:
            print(f"Exception: {str(e)}")
            return None

    def cleanUp(self, clean_path):
        if os.listdir(clean_path) != list():
            # iterate over the files and remove each file
            files = os.listdir(clean_path)
            for fileName in files:
                print(fileName)
                os.remove(os.path.join(clean_path, fileName))
        print("cleaned!")

@app.route("/", methods=['GET', 'POST'], defaults={"page_num": 1})
@app.route("/home/<int:page_num>", methods=['GET', 'POST'])
def home_page(page_num):
    books = Book.query.paginate(per_page=8, page=page_num, error_out=True)
    if request.method == 'POST' and 'tag' in request.form:
       tag = request.form["tag"]
       search = "%{}%".format(tag)
       #print(f"search: {search}")
       books = Book.query.filter(or_(Book.title.like(search), Book.rating.like(search),
                                     Book.age.like(search), Book.author.like(search),
                                     Book.year.like(search))).paginate(per_page=8, error_out=True)
       return render_template('home.html', books=books, tag=tag)
    return render_template('home.html', books=books)

@app.route("/details/<book_name>/<author_name>", methods=['GET', 'POST'])
def details_page(book_name, author_name):
    bookData = DataCollection(book_name, author_name)
    description = bookData.getDescription()
    reviewText = bookData.getReviewText()
    quoteText = bookData.getQuoteText()
    quoteTextRaw = bookData.getQuoteTextRaw()
    wordCloudReviewImg = None
    wordCloudProfanityImg = None
    grade_level = "graduate"
    if reviewText:
        #print(reviewText)
        profanity.load_censor_words()
        #print("Loaded censor words")
        profane_words = [lemma for lemma in word_tokenize(reviewText) if lemma in profanity.CENSOR_WORDSET]
        #print(profane_words)
        profane_review_set = " ".join(profane_words)
        wordCloudReviewImg = bookData.getWCImage(reviewText)

        if wordCloudReviewImg:
            wordCloudReviewImg = wordCloudReviewImg.decode('utf-8')

        if profane_review_set:
            wordCloudProfanityImg = bookData.getWCImage(profane_review_set)
            if wordCloudProfanityImg:
                print("Image Generated")
                wordCloudProfanityImg = wordCloudProfanityImg.decode('utf-8')

    if quoteTextRaw:
        #print(type(quoteTextRaw))
        readability_scores = Textatistic(quoteTextRaw).scores
        try:
            flesch_score = readability_scores['flesch_score']
        except Exception as e:
            print("Textatistic Exception")

        #print(f"Flesch Score is: {flesch_score}")
        if 90 <= flesch_score <= 100:
            grade_level = "Grade 5 and less"
        elif 80 <= flesch_score <= 90:
            grade_level = "Grade 6"
        elif 70 <= flesch_score <= 80:
            grade_level = "Grade 7"
        elif 60 <= flesch_score <= 70:
            grade_level = "Grade 8 & 9"
        elif 50 <= flesch_score <= 60:
            grade_level = "Grade 10 & 12"
        elif 30 <= flesch_score <= 50:
            grade_level = "College"
        else:
            grade_level = "Graduate"

    if quoteText:
        wordCloudQuoteImg = bookData.getWCImage(quoteText)
        if wordCloudQuoteImg:
            wordCloudQuoteImg = wordCloudQuoteImg.decode('utf-8')
    else:
        wordCloudQuoteImg = None

    #    full_filename = os.path.join(app.config['IMG_DIR'], book_name.lower().replace(" ", "_")+".png")
    return render_template('details.html', book_name=book_name, description=description,
                           review_wordcloud=wordCloudReviewImg,
                           profane_wordcloud=wordCloudProfanityImg,
                           quote_wordcloud=wordCloudQuoteImg,
                           grade_level=grade_level
                           )
