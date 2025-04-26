use base64::{engine::general_purpose::STANDARD, Engine as _};
use pyo3::prelude::*;
use std::fs::File;
use std::io::Read;

/*
Base64编码图像文件

Parameters
----------
image_path: &str
    图像文件路径

Returns
----------
String
    Base64编码的图像。若文件不存在，返回空字符串
*/
#[pyfunction]
pub fn chat_utils_media_handler_encode_image(image_path: &str) -> String {
    let mut buffer = Vec::new();
    File::open(image_path)
        .and_then(|mut f| f.read_to_end(&mut buffer))
        .map(|_| STANDARD.encode(&buffer))
        .unwrap_or_default()
}
