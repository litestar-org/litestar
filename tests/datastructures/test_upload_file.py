from os import urandom

from starlite import UploadFile


async def test_upload_file_methods() -> None:
    data = urandom(5)
    upload_file = UploadFile(content_type="application/text", filename="tmp.txt", max_spool_size=10, file_data=data)

    assert not upload_file.rolled_to_disk

    assert await upload_file.read() == data
    await upload_file.write(b"extra_data")

    assert upload_file.rolled_to_disk

    await upload_file.seek(5)  # type: ignore[unreachable]
    assert await upload_file.read() == b"extra_data"

    await upload_file.close()
    assert upload_file.file.closed
