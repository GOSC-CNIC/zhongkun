// tinymce通过filebrowser图片上传回调函数
function file_picker_callback(callback, value, type) {
    let cmsURL = '/admin/filebrowser/browse/?pop=5';
    cmsURL = cmsURL + '&type=' + type.filetype;

    if(value)
        cmsURL += '&input=';

    const instanceApi = tinyMCE.activeEditor.windowManager.openUrl({
        title: 'Select',
        url: cmsURL,
        width: 850,
        height: 650,
        inline: 'yse',
        buttons: [{name: 'btn-cancel',type: 'cancel', text: '取消', primary: true, align: 'end'}],
        onMessage: function(dialogApi, details) {
            callback(details.content);
            instanceApi.close();
        }
    });
    return false;
}



