// Manual Sync step 2
function manual_synchronization() {

   loading_done();

   $('#sd_frame_selector a').click(function() {
      var $t = $(this), $img = $t.find('img'), sd_id = $t.attr('data-rel');
      $('#sd_frame_selector a').removeClass('cur');
      $(this).addClass('cur');
      // Add image as preview bg
      $('#frame_selector_preview').css('background-image','url('+$img.attr('src')+')');
      // Add SD # to the preview
      $('#sd_id').html("SD#"+sd_id);

   })

   $('#hd_frame_selector a').click(function() {
      var $t = $(this), $img = $t.find('img'), hd_id = $t.attr('data-rel');
      $('#hd_frame_selector a').removeClass('cur');
      $(this).addClass('cur');
      // Add image as preview bg
      $('#hd_selector_preview').css('background-image','url('+$img.attr('src')+')');
      // Add SD # to the preview
      $('#hd_id').html("HD#"+hd_id);
   })  


   // Transparency
   $('#transparency').val(0.5).on('input', function () { 
         var val = parseInt($(this).val())/10;
         $('#hd_selector_preview').css('opacity',val);
   });  

   // Init .5 see above
   $('#hd_selector_preview').css('opacity',.5);


}


 
 



$(function() {

   // Go to manual sync step 1
   $('#manual_synchronization').click(function(){ 
      window.location = './webUI.py?cmd=manual_sync&json=' + json_file +'&video=' + main_vid + '&stack=' + my_image + '&type=HD'
   })

})
