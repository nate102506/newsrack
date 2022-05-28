"""
thediplomat.com
"""
from datetime import datetime, timedelta, timezone
import time
from urllib.parse import urlencode
import json
from html import unescape

from calibre.web.feeds.news import BasicNewsRecipe, classes
from calibre.ebooks.BeautifulSoup import BeautifulSoup

_name = "The Diplomat"


class TheDiplomat(BasicNewsRecipe):
    title = _name
    description = "The Diplomat is a current-affairs magazine for the Asia-Pacific, with news and analysis on politics, security, business, technology and life across the region."
    language = "en"
    __author__ = "ping"
    publication_type = "magazine"

    oldest_article = 7
    max_articles_per_feed = 25
    encoding = "utf-8"
    use_embedded_content = False
    no_stylesheets = True
    masthead_url = "https://thediplomat.com/wp-content/themes/td_theme_v3/assets/logo/diplomat_logo_black.svg"
    ignore_duplicate_articles = {"url"}

    compress_news_images = True
    scale_news_images = (800, 800)
    scale_news_images_to_device = False  # force img to be resized to scale_news_images
    auto_cleanup = False
    timeout = 20
    reverse_article_order = False
    timefmt = ""  # suppress date output
    pub_date = None  # custom publication date

    remove_attributes = ["style"]

    extra_css = """
    .headline { font-size: 1.8rem; margin-bottom: 0.5rem; }
    .sub-headline { font-size: 1.4rem; margin-top: 0; }
    .sub-headline p { margin-top: 0; }
    .article-meta { margin-bottom: 0.8rem; }
    .article-img { margin-bottom: 0.8rem; max-width: 100%; }
    .article-img img { display: block; max-width: 100%; height: auto; }
    .article-img .caption { display: block; font-size: 0.8rem; margin-top: 0.2rem; }
    .article-img .caption p { margin: 0; }
    """

    feeds = [
        (_name, "https://thediplomat.com/"),
    ]

    def _extract_featured_media(self, post):
        """
        Include featured media with post content.

        :param post: post dict
        :param post_content: Extracted post content
        :return:
        """
        post_content = post["content"]["rendered"]
        if not post.get("featured_media"):
            return post_content

        feature_media_links = post.get("_links", {}).get("wp:featuredmedia", [])
        br = self.get_browser()
        for i, feature in enumerate(feature_media_links, start=1):
            if not feature.get("embeddable"):
                continue
            feature_endpoint = feature.get("href")
            feature_info = json.loads(
                br.open_novisit(feature_endpoint).read().decode("utf-8")
            )

            # put feature media at the start of the post
            if feature_info.get("source_url"):
                caption = feature_info.get("caption", {}).get("rendered", "")
                # higher-res
                image_src = f"""
                <div class="article-img">
                    <img src="{feature_info["source_url"]}">
                    <div class="caption">{caption}</div>
                </div>"""
                post_content = image_src + post_content
            else:
                post_content = (
                    feature_info.get("description", {}).get("rendered", "")
                    + post_content
                )
        return post_content

    def preprocess_raw_html(self, raw_html, url):
        # formulate the api response into html
        post = json.loads(raw_html)
        post_date = datetime.strptime(post["date"], "%Y-%m-%dT%H:%M:%S")
        html = f"""<html>
        <head></head>
        <body>
            <h1 class="headline"></h1>
            <article data-og-link="{post["link"]}">
                <div class="sub-headline"></div>
                <div class="article-meta">
                    <span class="published-dt">{post_date:%-d %B, %Y}</span>
                </div>
            </div>
            </article>
        </body></html>"""
        soup = BeautifulSoup(html)
        title = soup.new_tag("title")
        title.string = unescape(post["title"]["rendered"])
        soup.body.h1.string = unescape(post["title"]["rendered"])
        soup.find("div", class_="sub-headline").append(
            BeautifulSoup(post["excerpt"]["rendered"])
        )
        soup.body.article.append(BeautifulSoup(self._extract_featured_media(post)))
        return str(soup)

    def populate_article_metadata(self, article, soup, first):
        # pick up the og link from preprocess_raw_html() and set it as url instead of the api endpoint
        og_link = soup.select("[data-og-link]")
        if og_link:
            article.url = og_link[0]["data-og-link"]
        article.title = soup.find("h1", class_="headline").string

    def publication_date(self):
        return self.pub_date

    def parse_index(self):
        br = self.get_browser()
        per_page = 100
        articles = {}

        for feed_name, feed_url in self.feeds:
            posts = []
            page = 1
            while True:
                cutoff_date = datetime.today().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=self.oldest_article)

                params = {
                    "rest_route": "/wp/v2/posts",
                    "page": page,
                    "per_page": per_page,
                    "after": cutoff_date.isoformat(),
                    "_": int(time.time() * 1000),
                }
                endpoint = f"{feed_url}?{urlencode(params)}"
                try:
                    res = br.open_novisit(endpoint)
                    posts_json_raw = res.read().decode("utf-8")
                    retrieved_posts = json.loads(posts_json_raw)
                    if not retrieved_posts:
                        break
                    posts.extend(retrieved_posts)
                    try:
                        # abort early to save one extra request
                        headers = res.info()
                        if headers.get("x-wp-totalpages"):
                            wp_totalpages = int(headers["x-wp-totalpages"])
                            if wp_totalpages == page:
                                break
                    except:
                        # do nothing else if we can't parse headers for page info
                        # rely on HTTP 400 to detect paging break
                        pass
                    page += 1
                except:  # HTTP 400
                    break

            latest_post_date = None
            for p in posts:
                post_update_dt = datetime.strptime(
                    p["modified_gmt"], "%Y-%m-%dT%H:%M:%S"
                ).replace(tzinfo=timezone.utc)
                if not self.pub_date or post_update_dt > self.pub_date:
                    self.pub_date = post_update_dt
                post_date = datetime.strptime(p["date"], "%Y-%m-%dT%H:%M:%S")
                if not latest_post_date or post_date > latest_post_date:
                    latest_post_date = post_date
                    self.title = f"{feed_name}: {post_date:%-d %b, %Y}"

                section_name = f"{post_date:%-d %B, %Y}"
                if len(self.get_feeds()) > 1:
                    section_name = f"{feed_name}: {post_date:%-d %B, %Y}"
                if section_name not in articles:
                    articles[section_name] = []
                params = {
                    "rest_route": f'/wp/v2/posts/{p["id"]}',
                    "_": int(time.time() * 1000),
                }
                endpoint = f"{feed_url}?{urlencode(params)}"
                articles[section_name].append(
                    {
                        "title": p["title"]["rendered"] or "Untitled",
                        "url": endpoint,
                        "date": f"{post_date:%-d %B, %Y}",
                        "description": p["excerpt"]["rendered"],
                    }
                )
        return articles.items()
