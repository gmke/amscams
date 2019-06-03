var $allframes;
var totalFrames;
var animationDuration;
var timePerFrame;
var timeWhenLastUpdate;
var timeFromLastUpdate;
var frameNumber; 
var playing;

// Modal for selector
function addAnimModalTemplate($allframes) {
    if($('#anim_modal').length === 0) {
        $('<div id="anim_modal" class="modal fade" tabindex="-1" role="dialog"><div class="modal-dialog modal-dialog-centered" role="document"><div class="modal-content"><div class="modal-body"><p><b>Frame by frame animation</b></p><div id="anim_holder"></div><div class="modal-footer p-0 pb-2 pr-2"><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>').appendTo('body');
        
        // Add all the frames
        $allframes.each(function(i,v) {
            $(this).clone().addClass('to_anim to_anim-'+i).appendTo('#anim_holder');
        });
    }
}

function frame_anim() { 
    $allframes = $('img.select_meteor');
    totalFrames = $allframes.length;
    animationDuration = parseFloat($('#dur').text())*1000; // Duration get the 
    timePerFrame = animationDuration / totalFrames;
    frameNumber = 1; 
    playing = true;

    addAnimModalTemplate($allframes);
    $('#anim_modal').modal();

    requestAnimationFrame(step);
}
  

// 'step' function will be called each time browser rerender the content
// we achieve that by passing 'step' as a parameter to 'requestAnimationFrame' function
function step(startTime) {
 

  // 'startTime' is provided by requestAnimationName function, and we can consider it as current time
  // first of all we calculate how much time has passed from the last time when frame was update
  if (!timeWhenLastUpdate) timeWhenLastUpdate = startTime;
  timeFromLastUpdate = startTime - timeWhenLastUpdate;

  // then we check if it is time to update the frame
  if (timeFromLastUpdate > timePerFrame) {
    
    $('.to_anim').css('opacity', 0); 
    $(`.to_anim-${frameNumber}`).css('opacity', 1);  
    timeWhenLastUpdate = startTime;
 
    if (frameNumber >= totalFrames) {
      frameNumber = 1;
    } else {
      frameNumber = frameNumber + 1;
    }        
  }

  if(playing) requestAnimationFrame(step);
}
 
$(function() {
    $('#play_anim').click(function() {
       playing = true;
       frame_anim();
    });

    $('#anim_modal').on('hidden.bs.modal', function () {
        playing = false; 
    })
      
})