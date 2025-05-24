use pyo3::prelude::*;

use crate::academic_utils::paper::academic_utils_paper_attach;

/*
将#attach{}命令替换为对应文件全文

Parameters
----------
text: &str
    待处理文本
current_dir: &str
    当前用户根目录

Returns
----------
String
    处理后文本
*/
#[pyfunction]
pub fn chat_utils_attachment_processor_process_attachments(
    text: &str,
    file_urls: Vec<String>,
) -> String {
    let mut new_text = String::with_capacity(512);
    for file in file_urls {
        let content = academic_utils_paper_attach(&file);
        if !content.is_empty() {
            new_text.push_str(&academic_utils_paper_attach(&file));
        }
    }
    new_text.push_str(text);
    new_text
}
