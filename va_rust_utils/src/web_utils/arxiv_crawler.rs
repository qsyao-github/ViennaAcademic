use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::Regex;
use scraper::{Html, Selector};

pub static REMOVE_HYPERLINK: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\[{1,2}([^\]]*)\]\([^)]*\)\]?").unwrap());

pub static REMOVE_CONSECUTIVE_NEWLINES: Lazy<Regex> = Lazy::new(|| Regex::new(r"\n{3,}").unwrap());
static ARTICLE_SELECTOR: Lazy<Selector> = Lazy::new(|| Selector::parse("article").unwrap());

#[pyfunction]
pub fn web_utils_arxiv_crawler_get_article_html(html_str: &str) -> String {
    // 解析HTML文档
    let document = Html::parse_document(html_str);

    // 查找匹配的元素
    document
        .select(&ARTICLE_SELECTOR)
        .next()
        .map(|e| e.html())
        .unwrap_or_default()
}

/*
清洗markdonify解析内容中的超链接和连续空行

Parameters
----------
markdown_content: &str
    待清洗的markdown内容

Returns
----------
String
    清洗后的markdown内容
*/
#[pyfunction]
pub fn web_utils_arxiv_crawler_process_markdown(markdown_content: &str) -> String {
    REMOVE_CONSECUTIVE_NEWLINES
        .replace_all(
            &REMOVE_HYPERLINK.replace_all(markdown_content, "[$1]"),
            "\n\n",
        )
        .trim()
        .into()
}
