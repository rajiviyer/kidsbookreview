from bs4 import BeautifulSoup
import requests
from datetime import datetime
from bookcollection.models import Book, Review, Quote
from bookcollection import db
import re

class urlParser():
    def __init__(self):
        self.dbname = 'sqlite:///books.db'
        self.url = "https://www.commonsensemedia.org"
        self.kwroute = "book-reviews"
        self.headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
                    }
        self.firefox_driver_path = "geckodriver.exe"
        self.book_review_url = "https://www.goodreads.com"
        self.command = "/search?q="
        self.quotes_command = "/work/quotes/"

    def drop_tables(self):
        db.drop_all()

    def create_tables(self):
        db.create_all()

    def quote_exist_db(self, book_id):
        return Quote.query.filter_by(book_id=book_id).first()

    def review_exist_db(self, book_id):
        return Review.query.filter_by(book_id=book_id).first()

    def book_exist_db(self, title):
        return Book.query.filter_by(title=title).first()

    def insert_books_mass(self):
        for book_list in self.find_books_list():
            book = self.book_exist_db(book_list[0])
            if not book:
                try:
                    new_book = Book(title=book_list[0], rating=book_list[1], description=book_list[2],
                                    age=book_list[3], author=book_list[4], year=book_list[5])
                    db.session.add(new_book)
                    db.session.commit()
                    book = self.book_exist_db(book_list[0])
                except Exception as e:
                    print(f"Error while inserting data for Book {book_list[0]}: {str(e)}")

            try:
                if not self.review_exist_db(book.id):
                    for review in self.get_book_reviews(book_list[0].split(", Book")[0]):
                        new_review = Review(review_text=review, book=book)
                        db.session.add(new_review)
                        db.session.commit()
                        print(f"Added Reviews for book {book_list[0]}")
                        print(review)
                    else:
                        continue

            except Exception as e:
                print(f"Exception in retrieving review for book {book_list[0]}: {str(e)}")

            try:
                if not self.quote_exist_db(book.id):
                    for quote in self.get_book_quotes(book_list[0].split(", Book")[0]):
                        new_quote = Quote(quote_text=quote, book=book)
                        db.session.add(new_quote)
                        db.session.commit()
                        print(f"Added Quote for book {book_list[0]}")
                        print(quote)
                    else:
                        continue
            except Exception as e:
                print(f"Exception in retrieving quote for book {book_list[0]}: {str(e)}")

    def find_books_list(self):
        for i in range(320):
            if i == 0:
                res = requests.get(self.url + "/" + self.kwroute, headers=self.headers)
            else:
                res = requests.get(self.url + "/" + self.kwroute + "?page=" + str(i), headers=self.headers)

            book_list_page = BeautifulSoup(res.content, features="html.parser")
            title_divs = book_list_page.select("div[class^=views-row]")
            # print("first item in list")
            # print(title_divs[0])
            for div in title_divs:
                title = div.findAll('div', {
                    'class': 'views-field views-field-field-reference-review-ent-prod result-title'})[0].text
                rating_divs = \
                div.findAll('div', {'class': 'views-field views-field-field-stars-rating inline rating-value'})[0]
                rating = rating_divs.findAll('div')[0]["class"][2].split("-")[1]
                description = div.findAll('div', {'class': 'views-field views-field-field-one-liner one-liner'})[
                    0].text
                age = div.findAll('div', {'class': 'csm-green-age'})[0].text
                author_divs = div.findAll('div', {'class': 'views-field views-field-field-term-book-authors '
                                                           'review-supplemental'})[0]
                author = author_divs.findAll('em', {'class': 'field-content'})[0].text
                year_divs = \
                div.findAll('div', {'class': 'views-field views-field-field-release-date review-supplemental'})[0]
                year = year_divs.findAll('span', {'class': 'nowrap-date'})[0].text
                # print("Title: " + title)
                # print("Rating: " + rating)
                # print("Description: " + description)
                # print("Author: " + author)
                # print("Year: " + year)
                yield [title.strip(), rating.strip(), description.strip(), age.strip().lstrip("age ").rstrip("+"),
                       author.strip(), year.strip()]

    def get_book_title_review(self, search_text):
        search_text = search_text.lower().replace(" ", "-")
        res = requests.get(self.book_review_url + self.command + search_text, headers=self.headers)
        main_page = BeautifulSoup(res.text, features="html.parser")
        title = main_page.findAll('a', {'class': 'bookTitle'})[0]['href'].split("?")[0]
        return title

    def get_book_title(self, search_text):
        search_text = search_text.lower().replace(" ", "-")
        res = requests.get(self.book_review_url + self.command + search_text, headers=self.headers)
        main_page = BeautifulSoup(res.text, features="html.parser")
        title = main_page.findAll('a', {'class': 'greyText', 'rel': 'nofollow'})[0]['href'].replace("/work/editions/", "")
        return title

    def get_book_reviews(self, book_name):
        title = self.get_book_title_review(book_name)
        review_links_res = requests.get(self.book_review_url + title)
        reviews_links_soup = BeautifulSoup(review_links_res.text, features="html.parser")
        review_divs = reviews_links_soup.findAll("div", {"id": "bookReviews"})[0]
        review_spans = review_divs.findAll('span', id=re.compile(r"reviewTextContainer\d.*"))
        for span in review_spans:
            txtContSpan = span.find("span", id=re.compile(r"freeTextContainer\d.*"))
            txtSpan = span.find("span", id=re.compile(r"freeText\d.*"))
            if txtSpan:
                yield txtSpan.get_text().strip()
            else:
                yield txtContSpan.get_text().strip()

    def get_book_quotes(self, book_name):
        title = self.get_book_title(book_name)
        quotes_res = requests.get(self.book_review_url + self.quotes_command + title)
        quotes_page = BeautifulSoup(quotes_res.text, features="html.parser")
        quotes_divs = quotes_page.findAll('div', {'class': 'quoteText'})
        #print(quotes_divs)
        for quotes in quotes_divs:
            quote_extracted = quotes.get_text().replace("\n", "").split("―")[0]
            quote_trimmed = quote_extracted.strip().lstrip("“").rstrip("”")
            yield quote_trimmed

    def retrieve_book_review(self, book_name):
        delay = 15
        driver = webdriver.Firefox()
        page_url = ""

    def retrieve_book_details(self, book_name):
        keyword = book_name
        res = requests.get(self.url + "/" + self.kwroute + "/" + keyword.replace(" ", "-"), headers=self.headers)
        print("URL: " + self.url + "/" + self.kwroute + "/" + keyword.replace(" ", "-"))
        review_page = BeautifulSoup(res.text, features="html.parser")

        print(type(review_page))
        title = review_page.find('h1').text
        review_items_ul = review_page.findAll('ul', {'id': 'review-product-details-list'})
        review_items_li = review_items_ul[0].findAll('li')
        # print(review_items_ul)
        # print(review_items_li)

        author = review_items_li[0].text.split(":")[1].lstrip()
        genre = review_items_li[1].text.split(":")[1].lstrip()
        book_type = review_items_li[2].text.split(":")[1].lstrip()
        publisher = review_items_li[3].text.split(":")[1].lstrip()
        publication_date = datetime.strptime(review_items_li[4].text.split(":")[1].lstrip(), "%B %d, %Y")
        recommended_age = review_items_li[5].text.split(":")[1].lstrip()
        total_pages = review_items_li[6].text.split(":")[1].lstrip()
        # print(title, author,genre, book_type, publisher, publication_date, recommended_age, total_pages)

        parents_desc_div = review_page.findAll('div', {'class': 'shutter-summary-pane panel-pane pane-entity-field '
                                                                'pane-node-field-parents-need-to-know with-foot'})
        parents_desc = parents_desc_div[0].findAll('p')[0].text
        # print(parents_desc)

        summary_div = review_page.findAll('div', {
            'class': 'shutter-summary-pane panel-pane pane-entity-field pane-node-field-what-is-story'})
        # print(summary_div)
        summary = ""
        for item in summary_div:
            summary += item.findAll('p')[0].text

        highlights_div = review_page.findAll('div', {
            'class': 'shutter-summary-pane panel-pane pane-entity-field pane-node-field-any-good'})
        highlights = ""

        for div in highlights_div:
            for p in div.findAll('p'):
                highlights += p.text

        # print(highlights)

        family_topics_div = review_page.findAll('div', {
            'class': 'shutter-summary-pane panel-pane pane-entity-field pane-node-field-family-topics'})
        family_topics = ""

        for div in family_topics_div:
            for p in div.findAll('p'):
                family_topics += p.text

        # print(family_topics)

        educational_divs = review_page.findAll('div', {'id': 'content-grid-item-educational'})
        educational_rating = \
            educational_divs[0].findAll('div', {'class': 'content-grid-rating'})[0]["class"][1].split("-")[-1]
        educational_text = educational_divs[0].findAll('p')[0].text
        # print(educational_text)

        message_divs = review_page.findAll('div', {'id': 'content-grid-item-message'})
        message_rating = message_divs[0].findAll('div', {'class': 'content-grid-rating'})[0]["class"][1].split("-")[
            -1]
        message_text = message_divs[0].findAll('p')[0].text
        # print(message_text)

        role_model_divs = review_page.findAll('div', {'id': 'content-grid-item-role_model'})
        role_model_rating = \
            role_model_divs[0].findAll('div', {'class': 'content-grid-rating'})[0]["class"][1].split("-")[-1]
        role_model_text = role_model_divs[0].findAll('p')[0].text
        # print(role_model_text)

        violence_divs = review_page.findAll('div', {'id': 'content-grid-item-violence'})
        violence_rating = \
            violence_divs[0].findAll('div', {'class': 'content-grid-rating'})[0]["class"][1].split("-")[-1]
        violence_text = violence_divs[0].findAll('p')[0].text
        # print(violence_text)

        adult_divs = review_page.findAll('div', {'id': 'content-grid-item-sex'})
        adult_rating = adult_divs[0].findAll('div', {'class': 'content-grid-rating'})[0]["class"][1].split("-")[-1]
        adult_text = adult_divs[0].findAll('p')[0].text
        # print(adult_text)

        language_divs = review_page.findAll('div', {'id': 'content-grid-item-language'})
        language_rating = \
            language_divs[0].findAll('div', {'class': 'content-grid-rating'})[0]["class"][1].split("-")[-1]
        language_text = language_divs[0].findAll('p')[0].text
        # print(language_text)

        consumerism_divs = review_page.findAll('div', {'id': 'content-grid-item-consumerism'})
        consumerism_rating = \
            consumerism_divs[0].findAll('div', {'class': 'content-grid-rating'})[0]["class"][1].split("-")[-1]
        consumerism_text = consumerism_divs[0].findAll('p')[0].text
        # print(consumerism_text)

        drugs_divs = review_page.findAll('div', {'id': 'content-grid-item-drugs'})
        drugs_rating = drugs_divs[0].findAll('div', {'class': 'content-grid-rating'})[0]["class"][1].split("-")[-1]
        drugs_text = drugs_divs[0].findAll('p')[0].text
        # print(drugs_text)
        book_review_list = [title, author, genre, book_type, publisher, publication_date,
                            recommended_age, total_pages, parents_desc, summary, highlights,
                            family_topics, educational_rating, educational_text, message_rating,
                            message_text, role_model_rating, role_model_text, violence_rating,
                            violence_text, adult_rating, adult_text, language_rating, language_text,
                            consumerism_rating, consumerism_text, drugs_rating, drugs_text
                            ]
        return book_review_list
