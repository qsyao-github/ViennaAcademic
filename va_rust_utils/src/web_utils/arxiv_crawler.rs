use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::Regex;

pub static REMOVE_HYPERLINK: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\[{1,2}([^\]]*)\]\([^)]*\)\]?").unwrap());

pub static REMOVE_CONSECUTIVE_NEWLINES: Lazy<Regex> = Lazy::new(|| Regex::new(r"\n{3,}").unwrap());

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
