use pyo3::prelude::*;

use lazy_static::lazy_static;
use regex::Regex;

const MIN_CHARACTER_THRESHOLD: usize = 63;

lazy_static! {
    static ref RE: Regex = Regex::new(r"\s*\n+\s*").unwrap();
}

// academic_utils
// paper
#[pyfunction]
pub fn academic_utils_paper_chunk(content: &str) -> Vec<String> {
    /*
    分段

    按换行符分段，确保每段长度大于63个字符

    Parameters
    ----------
    content: &str
        文本内容

    Returns
    ----------
    final_list: Vec<String>
        分段后的文本
    */
    let mut final_list = Vec::new();
    let mut temp_string = String::new();
    let mut char_count = 0;

    for para in RE.split(content) {
        let para_len = para.chars().count();
        temp_string.push_str(para);
        char_count += para_len;
        if char_count > MIN_CHARACTER_THRESHOLD {
            final_list.push(temp_string.clone());
            temp_string.clear();
            char_count = 0;
            continue;
        }
        temp_string.push_str("\n\n");
    }

    final_list.push(temp_string);

    final_list
}
