use pyo3::prelude::*;
use regex::Regex;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

const MIN_CHARACTER_THRESHOLD: usize = 63;

pub static SUFFIX_MAP: std::sync::LazyLock<std::collections::HashMap<&str, &str>> =
    std::sync::LazyLock::new(|| {
        HashMap::from([
            ("py", "python"),
            ("c", "c"),
            ("cpp", "cpp"),
            ("md", "markdown"),
            ("json", "json"),
            ("html", "html"),
            ("css", "css"),
            ("js", "javascript"),
            ("jinja2", "jinja2"),
            ("ts", "typescript"),
            ("yaml", "yaml"),
            ("dockerfile", "dockerfile"),
            ("sh", "shell"),
            ("r", "r"),
            ("sql", "sql"),
        ])
    });

pub static LINEBREAK_RE: std::sync::LazyLock<Regex> =
    std::sync::LazyLock::new(|| Regex::new(r"\s*\n+\s*").unwrap());

/*
附加文件内容

在knowledgeBase和code目录下查找文件。代码文件放入对应代码框中。由于参数是由Gradio端根据文件列表生成的，不应出现文件不存在的情况

Parameters
----------
file: &str
    文件名
current_user_directory: &str
    当前用户根目录

Returns
----------
String
    文件内容。若为代码则放入代码框
*/
#[pyfunction]
pub fn academic_utils_paper_attach(file: &str, current_user_directory: &str) -> String {
    let path = Path::new(file);
    let file_name = path.file_stem().unwrap().to_str().unwrap();
    let file_suffix = path.extension().unwrap_or_default().to_str().unwrap();
    let kb_path = Path::new(current_user_directory)
        .join("knowledgeBase")
        .join(format!("{file_name}.md"));
    if kb_path.exists() {
        return fs::read_to_string(kb_path).unwrap();
    }

    let code_path = Path::new(current_user_directory).join("code").join(file);
    if code_path.exists() {
        let code = fs::read_to_string(code_path).unwrap();
        let lang = SUFFIX_MAP.get(file_suffix).copied().unwrap_or("");
        return format!("```{lang}\n{code}\n```");
    }
    String::new()
}

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
#[pyfunction]
pub fn academic_utils_paper_chunk(content: &str) -> Vec<String> {
    let mut final_list = Vec::new();
    let mut temp_string = String::new();
    let mut char_count = 0;

    for para in LINEBREAK_RE.split(content) {
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
