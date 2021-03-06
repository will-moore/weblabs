from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.conf import settings
import os
import shutil

from omeroweb.webgateway import views as webgateway_views
from omeroweb.webclient.views import run_script
from omero.rtypes import wrap

try:
    from PIL import Image
except ImportError:
    import Image
from cStringIO import StringIO

from omeroweb.webclient.decorators import login_required


def index(request):
    """
    Just a place-holder while we get started
    """

    return HttpResponse("Welcome to weblabs!")


@login_required()
def fast_image_stack (request, imageId, conn=None, **kwargs):
    """ Load all the planes of image into viewer, so we have them all in hand for fast viewing of stack """
    
    image = conn.getObject("Image", long(imageId))
    z_indices = range(image.getSizeZ())
    return render_to_response('weblabs/image_viewers/fast_image_stack.html', {'image':image, 'z_indices':z_indices})


@login_required()
def max_intensity_indices (request, imageId, theC, conn=None, **kwargs):
    """ 
    Returns a 2D plane (same width and height as the image) where each 'pixel' value is
    the Z-index of the max intensity.
    """
    
    image = conn.getObject("Image", long(imageId))
    w = image.getSizeX()
    h = image.getSizeY()
    miPlane = [[0]*w for x in xrange(h)]
    indexPlane = [[0]*w for x in xrange(h)]
    
    pixels = image.getPrimaryPixels()
    
    c = int(theC)
    
    for z in range(image.getSizeZ()):
        plane = pixels.getPlane(z, c, 0)
        for x in range(w):
            for y in range(h):
                if plane[y][x] > miPlane[y][x]:
                    miPlane[y][x] = plane[y][x]
                    indexPlane[y][x] = z

    return HttpResponse(simplejson.dumps(indexPlane), mimetype='application/javascript')


@login_required()
def rotation_3d_viewer (request, imageId, conn=None, **kwargs):
    """ Shows an image viewer where the user can rotate the image in 3D using projections generated by ImageJ """

    image = conn.getObject("Image", long(imageId))
    default_z = image.getSizeZ() /2
    return render_to_response('weblabs/image_viewers/rotation_3d_viewer.html', {'image':image, 'default_z': default_z})


@login_required()
def rotation_proj_stitch (request, imageId, conn=None, **kwargs):
    """ 
    Use ImageJ to give 3D 'rotation projections' - stitch these into a single jpeg 
    so we can return them all as a single http response
    """

    region = request.REQUEST.get('region', None)    # x,y,w,h  option to use region of image
    axis = request.REQUEST.get('axis', 'Y')

    inimagejpath = "/Applications/ImageJ/ImageJ.app/Contents/Resources/Java/ij.jar" # Path to ij.jar
    rotation_ijm = """str=getArgument();
args=split(str,"*");
ippath=args[0];
slices=args[1];
opname=args[2];
oppath=args[3];

run("Image Sequence...", "open=&ippath number=&slices starting=1 increment=1 scale=100 file=[] or=[] sort");"""
    rotation_ijm += '\nrun("3D Project...", "projection=[Brightest Point] axis=%s-Axis slice=1 initial=0 total=360 rotation=10 lower=1 upper=255 opacity=0 surface=100 interior=50");'% axis
    rotation_ijm += '\nrun("Image Sequence... ", "format=JPEG name=[&opname] start=0 digits=4 save="+oppath );'
    
    image = conn.getObject("Image", long(imageId))
    sizeZ = image.getSizeZ()
    sizeX = image.getSizeX()
    sizeY = image.getSizeY()

    # need a directory where we can write temp files to exchage with ImageJ
    try:
        cache_dir = settings.CACHES['default']['LOCATION']
        if not os.path.exists(cache_dir):
            raise
    except:
        raise Http404("""No Cache Set. bin/omero config set omero.web.caches '{"default": {
                "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
                "LOCATION": "/var/tmp/django_cache"
            }}'""")

    rotation_dir = os.path.join(cache_dir, "rotation")
    tiff_stack = os.path.join(rotation_dir, "tiff_stack")
    destination = os.path.join(rotation_dir, "rot_rendered")
    ijm_path = os.path.join(rotation_dir, "rotation.ijm")
    try:
        os.mkdir(rotation_dir)
        os.mkdir(tiff_stack)
        os.mkdir(destination)
    except:
        pass # already exist, OK
    
    # write the macro to a known location (cache) we can pass to ImageJ
    f = open(ijm_path, 'w')
    f.write(rotation_ijm)
    f.close()
    theT = 0

    # getPlane() will either return us the region, OR the whole plane.
    if region is not None:
        x, y, w, h = region.split(",")
        def getPlane(z, t):
            rv = image.renderJpegRegion(z, t, x, y, w, h)
            if rv is not None:
                i = StringIO(rv)
                return Image.open(i)
    else:
        def getPlane(z, t):
            return image.renderImage(z, t)
        
    try:
        # Write a Z-stack to web cache
        for z in range(sizeZ):
            img_path = os.path.join(tiff_stack, "plane_%02d.tiff" % z)
            plane = getPlane(z, theT)   # get Plane (or region)
            plane.save(img_path)

        # Call ImageJ via command line, with macro ijm path & parameters
        macro_args = "*".join( [tiff_stack, str(sizeX), "rot_frame", destination])        # can't use ";" on Mac / Linu. Use "*"
        cmd = "java -jar %s -batch %s %s" % (inimagejpath, ijm_path, macro_args)
        os.system(cmd) #this calls the imagej macro and creates the 36 frames at each 10% and are then saved in the destination folder
        
        # let's stitch all the jpegs together, so they can be returned as single http response
        image_list=os.listdir(destination)
        stitch_width = plane.size[0] * len(image_list)
        stitch_height = plane.size[1]
        stiched = Image.new("RGB", (stitch_width,stitch_height), (255,255,255))
        x_pos = 0
        for i in image_list:
            img = Image.open(os.path.join(destination, i))
            stiched.paste(img, (x_pos, 0))
            x_pos += plane.size[0]
        rv = StringIO()
        stiched.save(rv, 'jpeg', quality=90)
        
    finally:
        # remove everything we've just created in the cache
        shutil.rmtree(rotation_dir)
    return HttpResponse(rv.getvalue(), mimetype='image/jpeg')


@login_required()
def scatter_gram (request, imageId, conn=None, **kwargs):
    """ Scattergram plot http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1993886/ 
    Load the data via AJAX using plane_as_json """
    
    image = conn.getObject("Image", long(imageId))
    default_z = image.getSizeZ() / 2
    return render_to_response('weblabs/image_viewers/scatter_gram.html', {'image':image, 'default_z':default_z})


@login_required()
def plane_as_json (request, imageId, theZ, theT, conn=None, **kwargs):
    """
    Returns a 2D plane (or planes) as json. Channel(s) are specified in 
    request as theC=1,2 or theC=0 etc. If more than one channel is
    requested, this will return an array of planes.
    """
    def RGBIntToRGBA(RGB, cCount):
    	""" 
    	Returns a tuple of (r,g,b,a) from an integer colour
    	r, g, b, a are 0-255. 

    	@param RGB:		A colour as integer. Int
    	@return:		A tuple of (r,g,b,a)
    	"""
    	r = (RGB >> 16) & 0xFF
    	g = (RGB >> 8) & 0xFF
    	b = (RGB >> 0) & 0xFF
    	return [r,g,b][0:cCount]    # slice to truncate if too long
    image = conn.getObject("Image", long(imageId))
    sizeX = image.getSizeX()
    sizeY = image.getSizeY()
    sizeC = image.getSizeC()

    if request.REQUEST.has_key('c'):
        channels, windows, colors =  webgateway_views._split_channel_info(request.REQUEST['c'])
        if len(channels) > 3:
            channels = channels[0:3]
    else:
        channels = (1,)     # 1-based indices
        colors = None

    minMax = [[c.getWindowMin(), c.getWindowMax()] for c in image.getChannels()]

    w = []
    for i, cIndex in enumerate(channels):
        print i, cIndex, windows[i], minMax[cIndex-1]
        if windows[i][0] is not None and windows[i][1] is not None:
            minMax[cIndex-1] = windows[i]
    
    colors = ['000']*sizeC      # up to 3 channels supported, returned as (r,g,b)
    rgb = ['F00', '0F0', '00F']
    for c, cIndex in enumerate(channels):
        colors[cIndex-1] = rgb[c]
    
    #print channels, minMax, colors
    image.setActiveChannels(channels, minMax, colors)
    
    z = int(theZ)
    t = int(theT)
    
    image._pd.z = long(z)
    image._pd.t = long(t)
    
    rv = image._re.renderAsPackedInt(image._pd)
    
    cCount = len(channels)
    plane = [RGBIntToRGBA(i, cCount) for i in rv]
    removeZeros = [i for i in plane if (10 not in i and 0 not in i)]

    return HttpResponse(simplejson.dumps(removeZeros), mimetype='application/javascript')


@login_required()
def render_settings (request, imageId, conn=None, **kwargs):
    """ Demo of 'render_settings' jQuery plugin - creates rendering controls for an image """

    image = conn.getObject("Image", imageId)
    default_z = image.getSizeZ() /2
    return render_to_response('weblabs/jquery_plugins/render_settings_plugin.html', {'image':image, 'default_z': default_z})


@login_required()
def backbone_render_pane (request, imageId, conn=None, **kwargs):
    """ Learning Backbone.js MVC - use it to generate a rendering control panel """

    image = conn.getObject("Image", imageId)
    default_z = image.getSizeZ() /2
    return render_to_response('weblabs/image_viewers/backbone_render_pane.html', {'image':image, 'default_z': default_z})


@login_required()
def viewport_test (request, imageId, conn=None, **kwargs):
    """ Just playing to learn viewport """

    image = conn.getObject("Image", imageId)
    default_z = image.getSizeZ() /2
    return render_to_response('weblabs/image_viewers/viewport_test.html', {'image':image, 'default_z': default_z})


@login_required()
def viewport_from_scratch (request, imageId, conn=None, **kwargs):
    """ Looking to rewrite the viewport, using separate components """
    
    image = conn.getObject("Image", imageId)
    default_z = image.getSizeZ() /2
    return render_to_response('weblabs/image_viewers/viewport_from_scratch.html', {'image':image, 'default_z': default_z})
    

#@login_required()
#def roi_backbone (request, imageId, conn=None, **kwargs):
#    """ ROI 'measurement tool' based on backbone.js """
#    
#    image = conn.getObject("Image", imageId)
#    default_z = image.getSizeZ() /2
#    return render_to_response('weblabs/raphael-backbone/paper.html', {'image':image, 'default_z': default_z})


@login_required()
def roi_backbone (request, imageId, conn=None, **kwargs):
    """
    This view is responsible for showing the omero_image template
    Image rendering options in request are used in the display page. See L{getImgDetailsFromReq}.
    
    @param request:     http request.
    @param iid:         Image ID
    @param conn:        L{omero.gateway.BlitzGateway}
    @param **kwargs:    Can be used to specify the html 'template' for rendering
    @return:            html page of image and metadata
    """
    iid = imageId
    from omeroweb.webgateway.views import getImgDetailsFromReq
    rid = getImgDetailsFromReq(request)
    
    image = conn.getObject("Image", iid)
    if image is None:
        logger.debug("(a)Image %s not found..." % (str(iid)))
        raise Http404
    d = {'blitzcon': conn,
         'image': image,
         'opts': rid,
         'roiCount': image.getROICount(),
         'viewport_server': kwargs.get('viewport_server', '/webgateway'),
         'object': 'image:%i' % int(iid)}

    template = kwargs.get('template', "weblabs/raphael-backbone/omero_image.html")
    return render_to_response(template, d)


@login_required()
def figureshop (request, conn=None, **kwargs):
    """
    Single page 'app' for creating a Figure, allowing you to choose images and lay them
    out in a customised table
    """

    return render_to_response("weblabs/figureshop.html", {})


@login_required(setGroupContext=True)
def make_web_figure(request, conn=None, **kwargs):
    """
    Uses the scripting service to generate pdf via json etc in POST data.
    Script will show up in the 'Activities' for users to monitor and download result etc.
    """
    if not request.method == 'POST':
        return HttpResponse("Need to use POST")

    scriptService = conn.getScriptService()
    sId = scriptService.getScriptID("/weblabs_scripts/Figure_To_Pdf.py")

    pageWidth = int(request.POST.get('pageWidth'))
    pageHeight = int(request.POST.get('pageHeight'))
    panelsJSON = str(request.POST.get('panelsJSON'))

    inputMap = {'Page_Width': wrap(pageWidth),
            'Page_Height': wrap(pageHeight),
            'Panels_JSON': wrap(panelsJSON)}

    rsp = run_script(request, conn, sId, inputMap, scriptName='Create Web Figure.pdf')
    return HttpResponse(simplejson.dumps(rsp), mimetype='json')
