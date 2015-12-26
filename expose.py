from collections import OrderedDict
from PIL import Image
from time import strptime, strftime
import json
import markdown
import os
import pprint
import re

inputFolder = "input"
imageTypes = ["jpg", "png", "gif"]
textTypes = ["txt", "md"]
md = markdown.Markdown(extensions = ['markdown.extensions.meta'])
imageIndex = 0

def natural_key(string_):
    """See http://www.codinghorror.com/blog/archives/001018.html"""
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_["sort"][0])]

def natural_key(string_):
    """See http://www.codinghorror.com/blog/archives/001018.html"""
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]


# --- helpers -----------------------------------------------------------------
def resizeImage(sourceImage, destinationImage, width):
	print("Resizing:", sourceImage)
	if not os.path.exists(os.path.dirname(destinationImage)):
		os.makedirs(os.path.dirname(destinationImage))
	img = Image.open(sourceImage)
	wpercent = (width/float(img.size[0]))
	hsize = int((float(img.size[1])*float(wpercent)))
	img = img.resize((width,hsize), Image.ANTIALIAS)
	#faster: img = img.resize((width,hsize))
	img.save(destinationImage)
	return destinationImage.replace("output/", "")


def getSnippet(buffer):
	global imageIndex
	html = ""

	date = buffer.get("meta", {}).get("date", ["none"])[0]
	if date is not "0":
		html += "<a name='" + date + "'></a>"

	# Text only
	if "text" in buffer and "image" not in buffer:
		template = getTemplate("content-text.html")		
		content = buffer["text"]
		html += template.replace("{{content}}", content)
		return html

	# Image only
	if "image" in buffer and "text" not in buffer:
		imageIndex += 1
		template = getTemplate("content-image.html")		
		outputImage = buffer["image"].replace("input", "output")
		content = resizeImage(buffer["image"], outputImage, 1000)
		contentbig = "../" + buffer["image"]
		template = template.replace("{{imageIndex}}", str(imageIndex))
		template = template.replace("{{content}}", content)
		template = template.replace("{{contentbig}}", contentbig)
		html += template
		return html

	# Text and Image
	if "image" in buffer and "text" in buffer:
		imageIndex += 1
		template = getTemplate("content-textimage.html")		
		outputImage = buffer["image"].replace("input", "output")
		content = resizeImage(buffer["image"], outputImage, 1000)
		contentbig = "../" + buffer["image"]
		type = buffer.get("meta", {}).get("type", ["default"])[0]
		style = getCSS(buffer)
		caption = buffer["text"]

		template = template.replace("{{content}}", content)
		template = template.replace("{{contentbig}}", contentbig)
		template = template.replace("{{imageIndex}}", str(imageIndex))
		template = template.replace("{{type}}", type)
		template = template.replace("{{style}}", style)
		template = template.replace("{{caption}}", caption)
		html += template
		return html


def getCSS(data):
	top = data.get("meta", {}).get("top", ["auto"])[0]
	left = data.get("meta", {}).get("left", ["auto"])[0]
	right = data.get("meta", {}).get("right", ["auto"])[0]
	bottom = data.get("meta", {}).get("bottom", ["auto"])[0]
	width = data.get("meta", {}).get("width", ["auto"])[0]
	height = data.get("meta", {}).get("height", ["auto"])[0]
	color = data.get("meta", {}).get("color", ["#fff"])[0]
	css = "top:" + str(top) + "; left:" + str(left) + "; right:" + str(right) + "; bottom: " + str(bottom) + "; width:" + str(width) + "; height:" + str(height) + "; color: " + str(color)
	return css


def getTemplate(templateName):
	with open("templates/"+ templateName, "r") as templateFile:
		return templateFile.read()


# --- extract data ------------------------------------------------------------
data = {}
dates = []
settings = {}
for root, dirs, files in os.walk(inputFolder):
	for file in files:
		filePath = os.path.join(root, file)
		fileParts = os.path.splitext(file)
		if file == "settings.json":
			with open("input/settings.json", "r") as settingsFile:
				settings = json.load(settingsFile)
			continue

		sorting = [sortingPart.lstrip("0") for sortingPart in fileParts[0].split("_")] 
		key = "_".join(sorting)
		ext = fileParts[-1].replace(".", "").lower()

		if key not in data:
			data[key] = {}

		if ext in imageTypes:
			filePath = filePath.replace("\\", "/")
			data[key]["image"] = filePath
		if ext in textTypes:
			with open(filePath, "r") as textFile:
				textContent = textFile.read()
				htmlContent = md.reset().convert(textContent)
				meta = md.Meta								
				data[key]["text"] = htmlContent				
				data[key]["meta"] = meta

				if "date" in meta:
					dateObject = strptime(meta.get("date")[0], "%Y-%m-%d")					
					dateItem = {
						"date": dateObject,
						"title": meta.get("title", "")
					}
					dates.append(dateItem)


# --- sort & arrange ----------------------------------------------------------
output = OrderedDict()
for d in data:
	sorting = d.split("_")
	i0 = int(sorting[0])
	i1 = int(sorting[1]) if len(sorting) > 1 else -1

	if i1 > 0:
		if i0 not in output:
			output[i0] = {"children": []}
		output[i0]["children"].append(data[d])
	else:
		output[i0] = data[d]

output = OrderedDict(sorted(output.items(), key=lambda t: t))
#todo: sort items with children


# --- generate html -----------------------------------------------------------
htmlTarget = "output/index.html"
if not os.path.exists("output"):
	os.makedirs("output")

templateBase = getTemplate("template.html")
templateCss = getTemplate("style.css")
templateItemSingle = getTemplate("item-single.html")
templateItemMultiple = getTemplate("item-multiple.html")
templateContentText = getTemplate("content-text.html")

template = templateBase.replace("{{css}}", templateCss)		

if not os.path.exists(os.path.dirname(htmlTarget)):
	os.makedirs(os.path.dirname(htmlTarget))

with open(htmlTarget, "w") as htmlFile:
	html = ""

	dateList = ""
	for date in dates:
		d = strftime("%Y-%m-%d", date.get("date"))
		label = strftime("%d.%m.%Y", date.get("date"))
		title = date.get("title", "")[0]
		if title is not "":
			label += " - " + title
		dateList += "<a href='#" + d + "'>" + label + "</a>"
	template = template.replace("{{dates}}", dateList)

	for o in output:
		if "children" in output[o]:
			childCount = str(len(output[o]["children"]))
			content = ""
			for child in output[o]["children"]:
				content += getSnippet(child)
			contentTemplate = getTemplate("item-multiple.html")
			contentTemplate = contentTemplate.replace("{{count}}", childCount)
			contentTemplate = contentTemplate.replace("{{content}}", content)
			html += contentTemplate
		else:
			content = getSnippet(output[o])
			contentTemplate = getTemplate("item-single.html")
			contentTemplate = contentTemplate.replace("{{content}}", content)
			html += contentTemplate

	template = template.replace("{{title}}", settings.get("title", "untitled"))		
	template = template.replace("{{expose}}", html)		
	htmlFile.write(template)
