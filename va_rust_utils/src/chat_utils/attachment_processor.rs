use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::Regex;

use crate::academic_utils::paper;

pub static ATTACH_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"#attach\{([^}]+)\}").unwrap());

/*
将#attach{}命令替换为对应文件全文

Parameters
----------
text: str
    待处理文本
current_dir: str
    当前用户根目录

Returns
----------
str
    处理后文本
*/
#[pyfunction]
pub fn chat_utils_attachment_processor_process_attachments(
    text: &str,
    current_dir: &str,
) -> String {
    ATTACH_RE
        .replace_all(text, |caps: &regex::Captures| {
            paper::academic_utils_paper_attach(&caps[1], current_dir)
        })
        .to_string()
}
