var CLMSUI = CLMSUI || {};

$(document).ready(function() {
    _.extend(window, Backbone.Events);
    window.onresize = function() {
        window.trigger('resize')
    };


    //having some problems with firefox
    CLMSUI.mzmlCbChecked = false;

    $("#submitDataModal").easyModal({
        overlayClose: false,
        closeOnEscape: false
    });

    $('#cancelUpload').click(function() {
        window.location.href = 'upload.php';
    });

    $('#errorMsg').on('click', '#showErrorLog', function() {
        $('#errorLog').toggle();
    });

    $('#fileupload').fileupload({
        dataType: 'json',
        fileTypes: "mzid|mzml|mgf|csv|zip|gz|fasta",
        // singleFileUploads: false,
        limitMultiFileUploadSize: 40000000,
        // Error and info messages:
        // messages: {
        //     uploadedBytes: 'Uploaded bytes exceed file size'
        // },
        maxChunkSize: 100000000, //100MB
        progressall: function(e, data) {
            var progress = parseInt(data.loaded / data.total * 100, 10);
            if (progress > 100) progress = 100; //quick&dirty fix to limit % to 100 (can happen if file is reuploaded)
            $('#uploadProgress .file_upload_bar').css(
                'width',
                progress + '%'
            );
            $('#uploadProgress .file_upload_percent').html(progress + '%');
        },
        add: function(e, data) {
            $('#startParsing').prop('disabled', true);

            if (new RegExp("\.(mzid|csv)(.gz)?$", 'i').test(data.files[0].name)) {
                $('#mzid_checkbox').prop("checked", false).change();
                $('#mzid_fileBox .fileName').html(data.files[0].name);
                data.context = $('#mzid_fileBox .statusBox').html('<div class="loader"></div>');
                data.submit();
            }

            if (new RegExp("\.(mzml|mgf|ms2|zip)(.gz)?$", 'i').test(data.files[0].name)) {
                CLMSUI.mzmlCbChecked = true;
                $('#mzml_checkbox').prop("checked", false).change();
                $('#mzml_fileBox .fileName').html(data.files[0].name);
                data.context = $('#mzml_fileBox .statusBox').html('<div class="loader"></div>');
                data.submit();
            }

            if (new RegExp("\.(fasta)$", 'i').test(data.files[0].name)) {
                $('#fasta_checkbox').prop("checked", false).change();
                $('#fasta_fileBox .fileName').html(data.files[0].name);
                data.context = $('#fasta_fileBox .statusBox').html('<div class="loader"></div>');
                data.submit();
            }

            var that = this;
            $.getJSON('upload-vendor-libs/jQueryFileUploadMin/fileUpload.php', {
                file: data.files[0].name
            }, function(result) {
                var file = result.file;
                data.uploadedBytes = file && file.size;
                $.blueimp.fileupload.prototype
                    .options.add.call(that, e, data);
            });

        },
        maxRetries: 100,
        retryTimeout: 500,
        fail: function(e, data) {
            // jQuery Widget Factory uses "namespace-widgetname" since version 1.10.0:
            var fu = $(this).data('blueimp-fileupload') || $(this).data('fileupload'),
                retries = data.context.data('retries') || 0,
                retry = function() {
                    $.getJSON('upload-vendor-libs/jQueryFileUploadMin/fileUpload.php', {
                            file: data.files[0].name
                        })
                        .done(function(result) {
                            var file = result.file;
                            data.uploadedBytes = file && file.size;
                            // clear the previous data:
                            data.data = null;
                            data.submit();
                        })
                        .fail(function() {
                            fu._trigger('fail', e, data);
                        });
                };
            if (data.errorThrown !== 'abort' &&
                data.uploadedBytes < data.files[0].size &&
                retries < fu.options.maxRetries) {
                retries += 1;
                data.context.data('retries', retries);
                window.setTimeout(retry, retries * fu.options.retryTimeout);
                return;
            }
            data.context.removeData('retries');
            if ($.blueimp.fileupload.prototype.options.fail) {
                $.blueimp.fileupload.prototype.options.fail.call(this, e, data);
            }
        },

        done: function(e, data) {
            if ($('#mzid_checkbox').prop("checked") == true) {
                $('#startParsing').prop('disabled', false);
            }
            if (data.context[0].dataset['filetype'] == 'mzml' || data.context[0].dataset['filetype'] == 'mgf') {
                CLMSUI.mzmlCbChecked = true;
                $('#mzml_checkbox').prop("checked", true).change();
            }
            if (data.context[0].dataset['filetype'] == 'mzid') {
                $('#mzid_checkbox').prop("checked", true).change();
                $('#startParsing').prop('disabled', false);
                $('#startParsing').css('color', 'white', 'important');
            }
            if (data.context[0].dataset['filetype'] == 'fasta') {
                $('#fasta_checkbox').prop("checked", true).change();
            }
            data.context.html('<span class="checkmark"><div class="checkmark_stem"></div><div class="checkmark_kick"></div></span>');
        }
    });

    $('#csvModificationsForm').submit(function(e) {
        e.preventDefault();
        var fd = $(this).serialize();
        $.ajax({
            url: "./php/submit_mods_for_csv.php",
            type: 'POST',
            data: fd,
            success: function(data) {
                $('#continueToDB').prop("disabled", false);
            }
        });
    });

    $('#ionsForm').submit(function(e) {
        e.preventDefault();
        var fd = $(this).serialize();
        var spinner = new Spinner({
            scale: 0.3
        }).spin();
        var target = d3.select('#ionsFormSubmit').node();
        $.ajax({
            url: "./php/update_ions.php",
            type: 'POST',
            data: fd,
            beforeSend: function() {
                $('#ionsFormSubmit').prop("disabled", true);
                target.appendChild(spinner.el);
                $('#ionsUpdateMsg').html('');
            },
            success: function(data) {
                spinner.stop();
                $('#ionsFormSubmit').prop("disabled", false);
                $('#ionsUpdateMsg').html('update successful!');
            }
        });
    });

    $('#continueToDB').click(function() {
        // if($('#csvModificationsForm input').length > 0)
        // 	$('#csvModificationsForm').submit();
        // if($('#ionsInfo').is(':visible'))
        // 	$('#ionsForm').submit();
        var identifier = $("input[name='identifier']").val();
        window.location.href = "./network.php?upload=" + identifier;
    });

    $("#startParsing").click(function(e) {
        e.preventDefault();
        var formData = new FormData();
        if (CLMSUI.mzmlCbChecked == true) {
            formData.append("peakFile_fn", $('#mzml_fileBox .fileName').html());
        } else {
            // alert("no peak list (debug message)");
        }
        formData.append("res_fn", $('#mzid_fileBox .fileName').html());
        CLMSUI.startParser(formData);

    });

    $('.ionSelectChkboxSubmit').change(function() {
        var ionSelectionArr = new Array();
        $('.ionSelectChkboxSubmit:checkbox:checked').each(function() {
            ionSelectionArr.push($(this).val());
        });
        if (ionSelectionArr.length == 0)
            $('#ionSelectionSubmit').val("Select ions...");
        else
            $('#ionSelectionSubmit').val(ionSelectionArr.join(", "));
    });

    CLMSUI.startParser = function(form_data) {
        var spinner = new Spinner({
            scale: 5
        }).spin();
        var target = d3.select("#processDataInfo > .spinnerWrapper").node();
        $.ajax({
            url: "./php/parse_data.php",
            type: 'POST',
            data: form_data,
            //async: false,
            contentType: false,
            processData: false,
            beforeSend: function() {
                $(".overlay").css("visibility", "visible").css("z-index", 1);
                target.appendChild(spinner.el);
                $("#processText").html("Your data is being processed. Please wait...</br>Depending on the size of your data this process may take up to several minutes.");
                $("#submitDataModal").trigger('openModal');
            },
            success: function(data) {
                spinner.stop();
                resp = JSON.parse(data);
                $('#submitDataInfo').append('<input class="form-control identifier" name="identifier" class="identifier" readonly type="text" value=' + resp.identifier + '>');
                $('#ionsForm').append('<input class="form-control identifier" name="identifier" class="identifier" readonly type="text" value=' + resp.identifier + '>');
                //alert(CLMSUI.mzmlCbChecked);
                if (resp.errors.length == 0 && (resp.modifications.length == 0 || CLMSUI.mzmlCbChecked == false) && resp.warnings.length == 0)
                    window.location.href = "../xi3/network.php?upload=" + resp.identifier;
                else {
                    $('#submitDataInfo').show();
                    $('#processDataInfo').hide();
                    $('#processText').html("");

                    var errorNum = resp.errors.length;
                    var warnNum = resp.warnings.length;
                    if (errorNum > 0 || warnNum > 0) {
                        $('#errorInfo').show();
                        $('#gitHubIssue').show();
                        $('#errorMsg').html(warnNum + ' warning(s) and ' + errorNum + ' error(s) occurred parsing your data.</br><a href="#" id="showErrorLog"><i class="fa fa-chevron-down" aria-hidden="true"></i>Show log for more information.<i class="fa fa-chevron-down" aria-hidden="true"></i></a>');
                        $('#errorLog').append('log id: ' + resp.log + ' (include this in the github issue)\n');

                        resp.warnings.forEach(function(warn) {
                            if (warn.type == 'IonParsing' && CLMSUI.mzmlCbChecked == true) {
                                $('#ionsInfo').show();
                                $('#ionsMsg').html('Your input file did not specify fragment ion types.</br>Select and update ion types below. Then click continue to view your data.');
                            }
                            $('#errorLog').append("warning type: " + warn.type + "\nmessage: " + warn.message + '\nid: ' + warn.id + '\n\n');

                        })

                        resp.errors.forEach(function(error) {
                            $('#errorLog').append("error type: " + error.type + "\nmessage: " + error.message + '\nid: ' + error.id + '\n\n');

                        })
                    }
                    if (CLMSUI.mzmlCbChecked == true) {
                        if (resp.modifications.length > 0) {
                            var getMass = function(name, data) {
                                for (var i = 0; i < data.data.length; i++) {
                                    var mod = data.data[i];
                                    if (mod.mod_name == name) {
                                        return mod.mass;
                                    }
                                }
                                return 0;
                            }

                            $.ajax({
                                url: "./php/get_modifications.php",
                                success: function(data) {
                                    data = JSON.parse(data);
                                    $('#continueToDB').prop('disabled', true);
                                    $('#modificationsInfo').show();
                                    $('#modificationsMsg').html("Please provide the mass(es) for the following " + resp.modifications.length + " modification(s):");
                                    $('#csvModificationsForm').append('<input class="form-control identifier" name="identifier" readonly type="text" value=' + resp.identifier + '>');

                                    resp.modifications.forEach(function(mod) {
                                        var modNameInput = '<input class="form-control" name="mods[]" readonly type="text" value=' + mod + '>';
                                        var value = getMass(mod, data);
                                        var modMassInput = '<input class="form-control" name="modMasses[]" type="number" step=0.000000001 value="' + value + '" required autocomplete=off>';
                                        $('#csvModificationsForm').append('<div style="margin-bottom: 5px;">' + modNameInput + modMassInput + '</div>');
                                    })
                                    $('#csvModificationsForm').append('<input type="submit" value="update modifications" class="btn btn-1a btn-2" id="updateModsSubmit">');
                                }
                            });
                        }
                    }
                }
                // var dialog = $("#submitDataModal");
                // var ml = -1 * dialog.width() / 2;
                // var mt = -1 * dialog.height() / 2;
                // dialog.css("margin-left", ml).css("margin-top", mt);// relayout?
                // $("#submitDataModal").dialog("option", "position", {my: "center", at: "center", of: window});
            }
        });
        return false;
    };

});
