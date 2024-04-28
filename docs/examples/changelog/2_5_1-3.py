class FileUpload(Struct):
    files: list[UploadFile]


@post(path="/")
async def upload_files_object(
    data: Annotated[FileUpload, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> list[str]:
    pass
