use pyo3::prelude::*;

mod academic_utils {
    pub mod paper;
}
use crate::academic_utils::paper::academic_utils_paper_attach;
use crate::academic_utils::paper::academic_utils_paper_chunk;
use crate::academic_utils::paper::LINEBREAK_RE;
use crate::academic_utils::paper::SUFFIX_MAP;

mod chat_utils {
    pub mod attachment_processor;
    pub mod media_handler;
    pub mod tool_formatter;
}
use crate::chat_utils::attachment_processor::chat_utils_attachment_processor_process_attachments;
use crate::chat_utils::attachment_processor::ATTACH_RE;
use crate::chat_utils::media_handler::chat_utils_media_handler_create_image_component;
use crate::chat_utils::media_handler::VALID_EXTS;
use crate::chat_utils::tool_formatter::chat_utils_tool_formatter_format_tools;
use crate::chat_utils::tool_formatter::TOOL_CALL_PATTERN;

mod file_utils {
    pub mod file_conversion;
}
use crate::file_utils::file_conversion::file_utils_file_conversion_markdown_to_everything;
use crate::file_utils::file_conversion::file_utils_file_conversion_pandoc_to_markdown;
use crate::file_utils::file_conversion::IMAGE_PATTERN;
use crate::file_utils::file_conversion::REMOVE_CITATION_PATTERN;

mod web_utils {
    pub mod arxiv_crawler;
}
use crate::web_utils::arxiv_crawler::web_utils_arxiv_crawler_extract_article;
use crate::web_utils::arxiv_crawler::web_utils_arxiv_crawler_process_markdown;
use crate::web_utils::arxiv_crawler::REMOVE_CONSECUTIVE_NEWLINES;
use crate::web_utils::arxiv_crawler::REMOVE_HYPERLINK;

/*
预热全局变量
*/
#[pyfunction]
fn initialize_static() {
    LINEBREAK_RE.split("Line1  \n\n  Line2");
    SUFFIX_MAP.get("py");
    ATTACH_RE.replace_all("#attach{some text}", "");
    TOOL_CALL_PATTERN.replace_all(r#"{ \n "tool_name": \n "arg_name""#, "");
    VALID_EXTS.contains(&"png");
    REMOVE_CITATION_PATTERN.replace_all("#cite(some text)", "");
    IMAGE_PATTERN.replace_all(
        r#"![](media/image1.png){width="6.718607830271216in"
height="3.8802088801399823in"}"#,
        "",
    );
    web_utils_arxiv_crawler_process_markdown(r#"<article></article>"#);
    REMOVE_CONSECUTIVE_NEWLINES.replace_all("Line1 \n\n\n Line2", "\n\n");
    REMOVE_HYPERLINK.replace_all("[[13](some_link)]", "[$1]");
}

#[pymodule]
fn va_rust_utils(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(initialize_static, m)?)?;
    m.add_function(wrap_pyfunction!(academic_utils_paper_attach, m)?)?;
    m.add_function(wrap_pyfunction!(academic_utils_paper_chunk, m)?)?;
    m.add_function(wrap_pyfunction!(
        chat_utils_attachment_processor_process_attachments,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        chat_utils_media_handler_create_image_component,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(chat_utils_tool_formatter_format_tools, m)?)?;
    m.add_function(wrap_pyfunction!(
        file_utils_file_conversion_markdown_to_everything,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        file_utils_file_conversion_pandoc_to_markdown,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        web_utils_arxiv_crawler_extract_article,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        web_utils_arxiv_crawler_process_markdown,
        m
    )?)?;
    Ok(())
}
