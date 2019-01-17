#!/usr/bin/env python
# wraphtml provides data container, template, def run_cmd - all return html
# vim: set expandtab nospell ft=none:
#"""
#call this module with:
#from wraphtml import WrapHtml
#"""

# imports #
import datetime
from bottle import SimpleTemplate, template
import subprocess
# End imports #

# globals #
tpl = SimpleTemplate("""
<html>
<head>
  <style>
    body {
        background: #000;
    }
    .container {
        background: -webkit-linear-gradient(top, #ACBDC8 0.0%, #6C7885 100.0%) no-repeat;
        border: 3px solid #333;
    }
    .center_box {
        background-color: lightgrey;
        margin: auto;
        width: 90%;
        border: 3px solid black;
        padding: 10px;
        margin-bottom: 4px;
        }
    .no_box {
        background-color: lightgrey;
        margin: auto;
        width: 100%;
        //text-overflow: clip;
        //border: 3px solid black;
        padding: 10px;
        padding-left: 20px;
        margin-bottom: 4px;
        }
    h2 {
        // font-family: Helvetica;
        font-family: Architects Daughter;
    }
    .footer {
        border-top: solid lightgrey 1px;
        padding-top: 3px;
        padding-left: 3px;
        padding-right: 3px;
        margin-right: 5px;
        margin-left: 5px;
        color: white;
        padding-bottom: 3px;
        border-bottom: solid lightgrey 1px;
        margin-bottom: 1px;
    }
    .fleft {
        float: left;
    }
    .fright {
        float: right;
    }
    table, th, td {
        border: 1px solid black;
    }
    div.title {
        margin-left: 5px;
        margin-right: 5px;
        margin-top: 10px;
        border-top: solid black 3px;
        text-align: center;
        font-size: 35px;
        border-bottom: solid black 2px;
        margin-bottom: 4px;
    }
    table, th, td {
	border: 1px solid black;
    `}
    .grid-container {
        display: grid;
        grid-template-columns: auto auto auto;
    }
    .grid-item {
        text-align: center;
    }
    #rc_logo {
     left: 30px;
     padding: 5px;
     position: absolute;
     color: #fff;
     font-size: 16px;
     font-family: Poppins;
     text-decoration: none;
    }
    #rc_logo a { 
    color: inherit; 
    text-decoration: none;
    } 
    .rc_nav {
      overflow: hidden;
      background-color: #363841;
      text-align: center;
      z-index: 6;
      margin: 4px 4px 4px 4px;
    }
    .rc_nav a {
     display: inline-block;
     margin-right: -4px;  /* inline-block gap fix */
     color: #fff;
     padding: 5px 10px 5px 10px;
     text-decoration: none;
     font-family: Poppins;
     font-size: 16px;
     -webkit-transition: background 0.3s linear;
     -moz-transition: background 0.3s linear;
     -ms-transition: background 0.3s linear;
     -o-transition: background 0.3s linear;
     transition: background 0.3s linear;
     z-index: 9;
    }
    .rc_nav a:hover {
      background-color: #575b69;
      color: #bdfe0e2;
    }
    .rc_nav .icon {
      display: none;
    }
    .rc_content {
      text-align: center; 
      padding-left:14px; 
      font-family: Poppins; 
      margin-top: 100px;  
      color: #8e909b;
    }
    @media screen and (max-width: 820px) {
      .rc_nav a {display: none;}
      .rc_nav a.icon {
        float: right;
        display: block;
        width: 60px;
      }
    }
    @media screen and (max-width: 820px) {
      .rc_nav.responsive {position: relative; top: 73px;}
      .rc_nav.responsive .icon {
        position: fixed;
        right: 0;
        top: 0;
      }
      .rc_nav.responsive a {
        float: none;
        display: block;
        text-align: center;
      }
    }
  </style>
</head>

<body>
<div class='container'>
	<div class='title'>
	 {{title}}
	</div> <!-- title -->

	% if defined('nav_d'):
    <!-- Top navigation -->
    %if nav_d:
        %if logo:
            <div id="rc_logo">
              <a href="{{org_link}}" title="Organization">{{org}}</a>
            </div>
        %end
    <div class="rc_nav">
    	%for k,v in nav_d.iteritems():
            <a href="{{v}}">{{k}}</a>
    	%end
    </div> 
    <br>
    %end

  % if center_box:
      <div class='center_box'>
  % else:
      <div class="no_box">
  % end

    {{!content}}
  </div>
	<br>

	<div class='footer'>
		<div class='grid-container'>
		<div class='grid-item' style='text-align: left;'>  {{!left}}  </div>
		<div class='grid-item' style='text-align: center'> {{center}} </div>
		<div class='grid-item' style='text-align: right;'> {{right}}  </div>
		</div> <!-- class=grid-container -->
	</div> <!-- class=footer -->

</div> <!-- continer -->
</script>
</body>
</html>
""")
# End globals #


# ## classes ## #
class WrapHtml:
    """
    WrapHtml: wraps content string with full html and style
    requires: content
    optional: set other attribute before calling <Object>.wrap_html
    Use:
        content = "my content"
        nav_d = {"one": "http://one.org", "two": "http://two.org", "three": "#three"}
        html = WrapHtml(content)
        html.title = "System Info"
        html.center = "sysinfo"
        html.nav_d = nav_d
        html.logo = True  # will put you org name on right of nav bar linked to home
        html.center_box = True
        output = html.wrap_html()
    Requires: 
        templates/html.tpl (built in here as a global)
    """
    def __init__(self, 
                 content="I need content!", 
                 title="Title", 
                 org="",
                 org_link="http://example.com",
                 center="",
                 right=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 
                 nav_d={},
                 logo=False, 
                 center_box=True
                 ):
        self.yr = datetime.datetime.now().strftime('%Y')
        self.content = content
        self.nav_d = nav_d
        self.title = title
        self.org = org
        self.org_link = org_link
        self.left = org + " &copy;" + datetime.datetime.now().strftime('%Y')
        self.center = center
        self.right = right
        self.logo = logo
        self.center_box = center_box
        self.output = ""

    def render(self):
        # self.output = template('templates/html', 
        try:
            self.content = unicode(self.content, errors='replace')
        except:
            pass
        self.output = template(
            tpl, 
            title = self.title, 
            content = self.content, 
            left = self.left, 
            center = self.center,
            right = self.right, 
            org = self.org,
            org_link = self.org_link,
            logo = self.logo,
            center_box = self.center_box,
            nav_d = self.nav_d,
            )
        return self.output
# End classes #


# def function()s #
def run_cmd(cmd, ret_type="str"):
    """
    run a command and return either a str or a list
    """
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
    # proc is now a str (possibly multiple lines with embedded '\n's but all in one str)
    if ret_type == "list":
        # turns the str into a list
        proc = proc.split("\n")
    if ret_type == "br":
        # this just turns all those \n chars into <br> for html use
        # this is kludgy but it works
        proc = proc.replace('\n','<br>')
    return proc
# End def function()s #


# ## main code ## #
if __name__ == '__main__':
    # this mostly for testing #
    content = "my content"
    nav_d = {"one": "http://one.org", "two": "http://two.org", "three": "#three"}
    html = WrapHtml(content)
    html.title = "System Info"
    html.center = "sysinfo"
    html.nav_d = nav_d
    print(html.render())
# ##### EOF ###### #
