
$(document).ready(function() {
	$('#registerexperiment .collapsible').change(function() {
		//$('#mycheckboxdiv').toggle();
		sensor_on_change(this.getAttribute('data-target'), this.checked);
	});
});

$(document).ready(function(){
    var $dropDown = $(".dropDown");
    var last_form_id = $(".dropDown").last().attr("id")

    $(".dropDown").each(function(){

       if (this.id == last_form_id){
            console.log("From if: " + this.id)
            if ($(this).val() == "False")
                $(this).nextUntil('h2').hide();
            else
                $(this).nextUntil('h2').show();
       } else {
            console.log("From else: " + this.id)
            if ($(this).val() == "False")
                $(this).nextUntil('h3').hide();
            else
                $(this).nextUntil('h3').show();
       }
    });

    $dropDown.change(function(){
        if ($(this).val() == "False"){
            //If the element is the last one of the sensors list
            if(this.id == last_form_id){
                $(this).nextUntil('h2').hide();
            } else {
                $(this).nextUntil('h3').hide();
            }
        } else {
           $(this).nextUntil('h3').show();
        }
    })
});