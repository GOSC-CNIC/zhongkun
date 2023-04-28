;'use strict';
(function () {
    let AZONES = {};    // 可用区
    let IMAGES = {};    // 缓存镜像信息
    let NETWORKS = {};    // 缓存网络信息
    let FLAVORS = {};    // 缓存网络信息

    function get_image_from_cache(index){
        if (IMAGES.hasOwnProperty(index)){
            return IMAGES[index];
        }
        return null;
    }
    function set_image_to_cache(index, html){
        IMAGES[index] = html;
    }

    function get_network_from_cache(index){
        if (NETWORKS.hasOwnProperty(index)){
            return NETWORKS[index];
        }
        return null;
    }
    function set_network_to_cache(index, html){
        NETWORKS[index] = html;
    }

    function get_flavor_from_cache(index){
        if (FLAVORS.hasOwnProperty(index)){
            return FLAVORS[index];
        }
        return null;
    }
    function set_flavor_to_cache(index, html){
        FLAVORS[index] = html;
    }

    function get_azone_from_cache(index){
        if (AZONES.hasOwnProperty(index)){
            return AZONES[index];
        }
        return null;
    }
    function set_azone_to_cache(index, html){
        AZONES[index] = html;
    }

    //
    // 页面刷新时执行
    window.onload = function() {
        update_select();
    };

    /*
     * 拼接params对象为url参数字符串
     * @param {Object} obj - 待拼接的对象
     * @returns {string} - 拼接成的query参数字符串
     */
    function encode_params(obj) {
        const params = [];

        Object.keys(obj).forEach((key) => {
            let value = obj[key];
            // 如果值为undefined我们将其置空
            if (typeof value === 'undefined') {
                value = ''
            }
            // 对于需要编码的文本我们要进行编码
            params.push([key, encodeURIComponent(value)].join('='))
        });

        return params.join('&');
    }

    // 校验创建虚拟机参数
    function valid_vm_create_data(obj){
        if(!obj.service_id || obj.service_id <= 0){
            alert('请选择服务端点');
            return false;
        }
        if (!obj.network_id){
            alert('请选择网络');
            return false;
        }
        if(!obj.image_id){
            alert('请选择系统镜像');
            return false;
        }
        if(!obj.flavor_id){
            alert('请选择配置');
            return false;
        }
        if (!obj.quota_id){
            delete obj.quota_id;
        }
        if (!obj.azone_id){
            delete obj.azone_id;
        }
        if (obj.pay_type !== 'prepaid'){
            delete obj.period;
        }
        return true;
    }

    // 创建虚拟机表单提交按钮点击事件
    $('form#id-form-server-create button[type="submit"]').click(function (e) {
        e.preventDefault(); // 兼容标准浏览器

        let form = $('form#id-form-server-create');
        let obj_data = getForm2Obj(form);
        if (!valid_vm_create_data(obj_data)){
            return;
        }
        if(!confirm('确定创建服务器实例？'))
            return;

        let api = build_absolute_url('api/server');
        let json_data = JSON.stringify(obj_data);
        let btn_submit = $(this);
        btn_submit.addClass('disabled'); //鼠标悬停时，使按钮表现为不可点击状态
        btn_submit.attr('disabled', true);//失能对应按钮
        $.ajax({
            url: api,
            type: 'post',
            data: json_data,
            contentType: 'application/json',
            success: function (data, status, xhr) {
                if (xhr.status === 200){
                    if(confirm('订购云主机成功,是否去服务器列表看看？')){
                        window.location = '/servers/';
                    }
                }else{
                    alert("创建失败！" + data.message);
                }
            },
            error: function (xhr) {
                let msg = '创建主机失败!';
                try{
                    msg = msg + xhr.responseJSON.message;
                }catch (e) {}
                alert(msg);
            },
            complete: function () {
                btn_submit.removeClass('disabled');   //鼠标悬停时，使按钮表现为可点击状态
                btn_submit.attr('disabled', false); //激活对应按钮
            }
        })
    });


    // 加载系统镜像下拉框渲染模板
    function render_image_select_items(data){
        let ret='<option value="">--</option>';
        let t = '<option value="{0}">{1}</option>';
        for(let i=0; i<data.length; i++){
            let s = t.format([data[i]['id'], data[i]['name']]);
            ret = ret.concat(s);
        }
        return ret;
    }

    function image_select_clear(){
        let html='<option value="">--</option>';
        let image_select = $('select[name="image_id"]');
        image_select.html(html);
    }

    function image_select_update(){
        let service = $('select[name="service_id"]').val();
        let azone_id = $('select[name="azone_id"]').val();
        let flavor_id = $('select[name="flavor_id"]').val();
        let index_key = service + '_' + azone_id;
        if (!service)
            return;

        let html = get_image_from_cache(index_key);
        let image_select = $('select[name="image_id"]');
        if (html !== null){
            image_select.html(html);
            return;
        }
        image_select.html('');
        let query_str = encode_params({service_id:service, flavor_id: flavor_id});
        $.ajax({
            url: build_absolute_url('api/image?'+ query_str),
            type: 'get',
            contentType: 'application/json',
            success: function (data, status, xhr) {
                let html = render_image_select_items(data.results);
                image_select.html(html);
                set_image_to_cache(index_key, html);
            },
            error: function (xhr) {
                let msg = '获取镜像数据失败!';
                try{
                    msg = msg + xhr.responseJSON.message;
                }catch (e) {}
                alert(msg);
            }
        });
    }

    // 加载配置下拉框渲染模板
    function render_flavor_select_items(data){
        let ret='<option value="">--</option>';
        let t = '<option value="{0}">vCPU:{1}/RAM:{2}GB</option>';
        for(let i=0; i<data.length; i++){
            let s = t.format([data[i]['id'], data[i]['vcpus'], data[i]['ram_gib']]);
            ret = ret.concat(s);
        }
        return ret;
    }

    function flavor_select_update(){
        let service = $('select[name="service_id"]').val();
        let azone_id = $('select[name="azone_id"]').val();
        let index_key = service + '_' + azone_id;
        if (!service)
            return;

        let flavor_select = $('select[name="flavor_id"]');
        let html = get_flavor_from_cache(index_key);
        if (html !== null){
            flavor_select.html(html);
            return;
        }

        let query_str = encode_params({service_id:service});
        $.ajax({
            url: build_absolute_url('api/flavor?'+ query_str),
            type: 'get',
            contentType: 'application/json',
            success: function (data, status, xhr) {
                let html = render_flavor_select_items(data['flavors']);
                flavor_select.html(html);
                set_flavor_to_cache(index_key, html);
            },
            error: function (xhr) {
                let msg = '获取配置样式数据失败!';
                try{
                    msg = msg + xhr.responseJSON.message;
                }catch (e) {}
                alert(msg);
            }
        });
    }

    // 加载配置下拉框渲染模板
    function render_quota_select_items(data){
        let ret='<option value="">--</option>';
        let t = `<option value="{id}">
                    [{tag}](vCPU: {vcpu}, RAM: {ram}MB, PublicIP: {publicIp}, PrivateIP: {privateIp}, Disk: {disk}Gb);有效期至：{etime}
                 </option>'`;
        for(let i=0; i<data.length; i++){
            let quota = data[i];
            let etime = isoTimeToLocal(quota.expiration_time);
            if (!etime){
                etime = '无';
            }
            let d = {
                id: quota.id,
                tag: quota.tag.display,
                vcpu: quota.vcpu_total - quota.vcpu_used,
                ram: quota.ram_total - quota.ram_used,
                publicIp: quota.public_ip_total - quota.public_ip_used,
                privateIp: quota.private_ip_total - quota.private_ip_used,
                disk: quota.disk_size_total - quota.disk_size_used,
                etime: etime
            };
            let s = t.format(d);
            ret = ret.concat(s);
        }
        return ret;
    }


     // 加载网络下拉框渲染模板
    function render_network_select_items(data){
        let ret='<option value="" style="display: none">--</option>';
        let t = '<option value="{0}" data-tag="{1}">{2}</option>';
        for(let i=0; i<data.length; i++){
            let s = t.format([data[i]['id'], data[i]['public'], data[i]['name']]);
            ret = ret.concat(s);
        }
        return ret;
    }
    function network_select_update(){
        let service = $('select[name="service_id"]').val();
        let azone_id = $('select[name="azone_id"]').val();
        let index_key = service + '_' + azone_id;
        if (!service)
            return;

        let html = get_network_from_cache(index_key);
        let network_select = $('select[name="network_id"]');
        if (html !== null){
            network_select.html(html);
            return;
        }
        network_select.html('');
        querys = {service_id:service}
        if (azone_id){
            querys['azone_id'] = azone_id
        }
        let query_str = encode_params(querys);
        $.ajax({
            url: build_absolute_url('api/network?'+ query_str),
            type: 'get',
            contentType: 'application/json',
            success: function (data, status, xhr) {
                let html = render_network_select_items(data);
                network_select.html(html);
                set_network_to_cache(index_key, html)
            },
            error: function (xhr) {
                let msg = '获取网络数据失败!';
                try{
                    msg = msg + xhr.responseJSON.message;
                }catch (e) {}
                alert(msg);
            }
        });
    }

    $("#id-network-tag").change(function (e){
        e.preventDefault();

        let tag = $("#id-network-tag").val();
        let select_network = $('#id-network');
        if (tag === "1"){
            select_network.find('option[data-tag="true"]').attr("style", "display: block");
            select_network.find('option[data-tag="false"]').attr("style", "display: none");
            select_network.find('option').prop("selected",'');
        }else if (tag === "2"){
            $('#id-network option[data-tag="true"]').attr("style", "display: none");
            $('#id-network option[data-tag="false"]').attr("style", "display: block");
            select_network.find('option').prop("selected",'');
        }else {
            $('#id-network option').attr("style", "display: block");
        }
    });

    // 加载可用区下拉框渲染模板
    function render_azone_select_items(data){
        let ret='<option value="">--</option>';
        let t = '<option value="{0}">{1}</option>';
        for(let i=0; i<data.length; i++){
            let s = t.format([data[i]['id'], data[i]['name']]);
            ret = ret.concat(s);
        }
        return ret;
    }

    function azone_select_update(){
        let service = $('select[name="service_id"]').val();
        if (!service)
            return;

        let azone_select = $('select[name="azone_id"]');
        let html = get_azone_from_cache(service);
        if (html !== null){
            azone_select.html(html);
            return;
        }
        azone_select.html('');
        let query_str = encode_params({service_id:service});
        $.ajax({
            url: build_absolute_url('api/azone?'+ query_str),
            type: 'get',
            contentType: 'application/json',
            success: function (data, status, xhr) {
                let html = render_azone_select_items(data['zones']);
                azone_select.html(html);
                set_azone_to_cache(service, html);
            },
            error: function (xhr) {
                let msg = '获取服务可用区数据失败!';
                try{
                    msg = msg + xhr.responseJSON.message;
                }catch (e) {}
                alert(msg);
            }
        });
    }

    function update_select(){
        azone_select_update();
        // image_select_update();
        image_select_clear();
        flavor_select_update();
        network_select_update();
    }

    $("#id-service").change(function (e) {
        e.preventDefault();
        azone_select_update();
        // image_select_update();
        image_select_clear();
        network_select_update();
    });

    $("#id-azone").change(function (e) {
        e.preventDefault();
        network_select_update();
    });

    $("#id-flavor").change(function (e) {
        e.preventDefault();
        image_select_update();
    });

})();

