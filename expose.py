from collections import OrderedDict
import jinja2
import json
import markdown
import shutil
import os
import re
from time import strptime, strftime
from PIL import Image


# --- global variables --------------------------------------------------------
imageTypes = ["jpg", "png", "gif"]
videoTypes = ["mp4"]
textTypes = ["txt", "md"]
markdownParser = markdown.Markdown(extensions = ["markdown.extensions.meta"])

settings = {}


# --- Directory parsing -------------------------------------------------------
def parseDirectory(directory):
	global settings

	filePattern = re.compile("(\d+)(_?)(\d*).(\w+)")
	items = {}

	for name in os.listdir(directory):			
		match = filePattern.match(name)
		if match:
			key = match.group(1)
			subkey = match.group(3)
			type = match.group(4).lower()

			if key not in items:
				items[key] = {}

			if subkey and "children" not in items[key]:
				items[key]["children"] = {}

			if subkey and subkey not in items[key]["children"]:
				items[key]["children"][subkey] = {}

			if type in imageTypes:
				if subkey:
					items[key]["children"][subkey]["image"] = match.group(0)
				else:
					items[key]["image"] = match.group(0)

			if type in videoTypes:
				if subkey:
					items[key]["children"][subkey]["video"] = match.group(0)
				else:
					items[key]["video"] = match.group(0)

			if type in textTypes:
				with open(os.path.join(directory, name), "r") as textFile:
					content = markdownParser.reset().convert(textFile.read())
					meta = markdownParser.Meta

					if subkey:
						items[key]["children"][subkey]["text"] = content
						if meta:
							items[key]["children"][subkey]["meta"] = meta
					else:
						items[key]["text"] = content
						if meta:
							items[key]["meta"] = meta

	return items


def listDirectories():
	directories = {}
	directoryPattern = re.compile("(\d+) - (.+)")
	for root, dirs, files in os.walk("."):
		for dir in dirs:
			match = directoryPattern.match(dir)
			if match:
				items = parseDirectory(os.path.join(root, dir))				
				key = match.group(1)
				name = match.group(2)								
				directory = {
					"dir": dir,
					"root": root,
					"name": name,
					"items": items,
					"count": len(items)
				}

				# set settings if available
				if os.path.isfile(os.path.join(root, dir, "settings.json")):
					with open(os.path.join(root, dir, "settings.json"), "r") as settingsFile:
						directory["settings"] = json.load(settingsFile)

				rootFolder = root.split("\\")[-1:][0]

				if rootFolder is ".":
					directories[key] = directory					
					directories[key]["children"] = {}
					directories[key]["childcount"] = 0
				else:
					rootMatch = directoryPattern.match(rootFolder)
					rootKey = rootMatch.group(1)
					rootName = rootMatch.group(2)

					directories[rootKey]["children"][key] = directory					
					directories[rootKey]["childcount"] += 1

	return directories


def orderDictionary(content):
	content = OrderedDict(sorted(content.items(), key=lambda t: t))		
	for c in content:
		if "items" in content[c]:
			content[c]["items"] = orderDictionary(content[c]["items"])
		if "children" in content[c]:
			content[c]["children"] = orderDictionary(content[c]["children"])
	return content


def folderize(content):
	if not os.path.exists("output"):
		os.makedirs("output")

	for c in content:
		createImages("output", content[c])
		createHtml("output", content[c])


def createImages(root, content):
	folderName = content["name"].lower().replace(" ", "_")
	target = os.path.join(root, folderName)
	origin = os.path.join(content["root"], content["dir"])

	# create folder
	if not os.path.exists(target):
		os.makedirs(target)

	# copy images
	if "items" in content:
		for item in content["items"]:
			if "image" in content["items"][item]:
				imageName = content["items"][item]["image"]
				imageOrigin = os.path.join(origin, imageName)
				imageTarget = os.path.join(target, imageName)
				createImage(imageOrigin, imageTarget, 1000)

			if "video" in content["items"][item]:
				videoName = content["items"][item]["video"]
				videoOrigin = os.path.join(origin, videoName)
				videoTarget = os.path.join(target, videoName)
				createVideo(videoOrigin, videoTarget)


			if "children" in content["items"][item]:
				for child in content["items"][item]["children"]:
					if "image" in content["items"][item]["children"][child]:
						imageName = content["items"][item]["children"][child]["image"]
						imageOrigin = os.path.join(origin, imageName)
						imageTarget = os.path.join(target, imageName)
						createImage(imageOrigin, imageTarget, 1000)

					if "video" in content["items"][item]["children"][child]:
						videoName = content["items"][item]["children"][child]["video"]
						videoOrigin = os.path.join(origin, videoName)
						videoTarget = os.path.join(target, videoName)
						createVideo(videoOrigin, videoTarget)

	if "children" in content:
		for child in content["children"]:
			folderName = content["children"][child]["name"].lower().replace(" ", "_")
			titleOrigin = os.path.join(content["children"][child]["root"], content["children"][child]["dir"], "title.jpg")		
			titleTarget = os.path.join(target, folderName, "title.jpg")
			createImage(titleOrigin, titleTarget, 1000)

			createImages(target, content["children"][child])


def createImage(origin, target, width):
	targetPath = target.split(os.path.sep)
	targetPath.pop()
	targetPath = os.path.sep.join(targetPath)
	if not os.path.exists(targetPath):
		os.makedirs(targetPath)

	img = Image.open(origin)
	height = int(width * (img.size[1] / img.size[0]))
	#img = img.resize((width, height), Image.ANTIALIAS)
	img = img.resize((width, height))
	img.save(target)


def createVideo(origin, target):
	shutil.copy(origin, target)


def createHtml(root, content):
	folderName = content["name"].lower().replace(" ", "_")
	target = os.path.join(root, folderName)
	htmlTarget = os.path.join(target, "index.html")

	createHtmlPage(htmlTarget, content)

	if "children" in content:
		for child in content["children"]:
			createHtml(target, content["children"][child])


def createHtmlPage(target, content):
	templateLoader = jinja2.FileSystemLoader(searchpath="templates")
	templateEnv = jinja2.Environment(loader=templateLoader)
	template = templateEnv.get_template("photoset.html")

	nav = []

	items = []
	if "items" in content:
		for item in content["items"]:
			items.append(content["items"][item])
			if "meta" in content["items"][item]:
				date = content["items"][item]["meta"]["date"][0]
				timestamp = strptime(date, "%Y-%m-%d")
				title = content["items"][item]["meta"]["title"][0]
				nav.append({
					"target": "#" + date,
					"timestamp": strftime("%d.%m.%Y", timestamp),
					"label": title
				})

	children = []
	if "children" in content:
		for child in content["children"]:
			children.append(content["children"][child])

	templateVars = {
		"name": content["name"],
		"items": items,
		"children": children,
		"navigation": nav
	}
	outputText = template.render(templateVars)
	with open(target, "w") as html:
		html.write(outputText)


def createOverview(content):
	templateLoader = jinja2.FileSystemLoader(searchpath="templates")
	templateEnv = jinja2.Environment(loader=templateLoader)
	template = templateEnv.get_template("overview.html")

	sets = []
	for c in content:
		sets.append(content[c])
		titleOrigin = os.path.join(content[c]["dir"], "title.jpg")
		titleTarget = os.path.join("output", content[c]["name"].lower().replace(" ", "_"), "title.jpg")
		createImage(titleOrigin, titleTarget, 1000)

	settings = {}
	with open("settings.json", "r") as settingsFile:
		settings = json.load(settingsFile)

	templateVars = {
		"sets": sets,
		"settings": settings
	}

	outputText = template.render(templateVars)
	with open("output/index.html", "w") as html:
		html.write(outputText)

	# copy css
	shutil.copy("templates/style.css", "output/style.css")


# --- Startup -----------------------------------------------------------------
content = listDirectories()
content = orderDictionary(content)

folderize(content)
createOverview(content)
