use pyo3::prelude::*;
use regex::Regex;

static COMBINED_REGEX: std::sync::LazyLock<Regex> =
    std::sync::LazyLock::new(|| Regex::new(r"\[{1,2}([^\]]*)\]\([^)]*\)\]?|\n{3,}").unwrap());

/*
提取Arxiv论文正文部分

Parameters
----------
html: &str
    完整html

Returns
----------
&str
    正文html，若没有正文则为空字符串
*/
#[pyfunction]
pub fn web_utils_arxiv_crawler_extract_article(html: &str) -> &str {
    let Some(start) = html.find("<article") else {
        return "";
    };
    let body_start = match html[start..].find('>') {
        Some(pos) => start + pos + 2,
        None => return "",
    };
    html[body_start..]
        .rfind("</article>")
        .map_or("", |end| &html[body_start..body_start + end - 1])
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
    COMBINED_REGEX
        .replace_all(markdown_content, |caps: &regex::Captures| {
            caps.get(1).map_or_else(
                || "\n\n".to_string(),
                |link_text| format!("[{}]", link_text.as_str()),
            )
        })
        .trim()
        .into()
}
