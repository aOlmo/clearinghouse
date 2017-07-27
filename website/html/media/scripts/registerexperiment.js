
// The following code was made to collapse the sensor forms,
// TODO: It can be improved if instead of hiding everything until the next
// <h2> or <h3> tag, each form was within a div and hide this one instead.
$(document).ready(function(){
    var $dropDown = $(".dropDown");
    var last_form_id = $(".dropDown").last().attr("id")

    $(".dropDown").each(function(){

       if (this.id == last_form_id){
            if ($(this).val() == "False")
                $(this).nextUntil('h2').hide();
            else
                $(this).nextUntil('h2').show();
       } else {
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