window.addEventListener("load", function(){

    var select = document.getElementById('operation');
    var x = document.getElementById('transfer');
    var list = document.getElementById('conta').options
    var selection = "<label class='lau'>Account receiving:</label> <select class='form-control' name='receive'>"

    for (let i = 0; i < list.length; i++)
    {
        selection += "<option value=" + list[i].value + ">" + list[i].value + "</option>"
    }
    selection += '</select>'

    select.addEventListener('change', function(){

        var value = select.options[select.selectedIndex].value;
        console.log(select, value, x, list);
        if ( value == "Transfer")
        {
            x.innerHTML = selection;
        }
        else
        {
            x.innerHTML = "";
        }

    });

});

$(document).ready(function() {
    $('.js-example-basic-multiple').select2();
});