#!/usr/bin/env python

# Installation
# PIP: pip install pypdf openxmllib
# OSX: brew install exiftool ffmpeg
# APT: apt-get install exiftool ffmpeg

import os
import types
import sys
import StringIO
import subprocess
from optparse import OptionParser, OptionGroup
import pyPdf
import openxmllib

VERSION = 0.9

# Mapper for matching extensions to metadata classes for extraction and scrubbing
EXTENSIONS = {
	"flv": "exif",
	"gif": "exif",
	"jpg": "exif",
	"jpeg": "exif",
	"mov": "ffmpeg",
	"mp4": "exif",
	"mpg": "ffmpeg",
	"wmv": "ffmpeg",
	"pdf": "pdf",
	"png": "exif",
	"docx": "openxml",
	"pptx": "openxml",
}


def autoclass(filepath):
	document = False
	filepath = os.path.realpath(filepath)
	extension = os.path.splitext(filepath)[1].lower().split(".")[-1]
	if not extension or not extension in EXTENSIONS:
		return False
	if EXTENSIONS[extension] == "exif":
		document = exif(filepath)
	if EXTENSIONS[extension] == "ffmpeg":
		document = ffmpeg(filepath)
	if EXTENSIONS[extension] == "pdf":
		document = pdf(filepath)
	if EXTENSIONS[extension] == "openxml":
		document = openxml(filepath)
	return document


class exif:
	def __init__(self, filepath):
		self.scrubbing = True
		self.filepath = filepath
		return

	def metadata(self):
		tags = {}
		output = subprocess.Popen(["exiftool", self.filepath], stdout=subprocess.PIPE).communicate()[0]
		lines = output.split("\n")
		for line in lines:
			line = line.split(":", 1)
			if len(line) == 2:
				tags[line[0].strip()] = line[1].strip()
		return tags

	def scrub(self):
		output = subprocess.Popen(["exiftool", "-all=", "-o", "metascrub_tmp", self.filepath], stdout=subprocess.PIPE).communicate()[0]
		f = open("./metascrub_tmp", "rb")
		string = f.read()
		f.close()
		os.remove("metascrub_tmp")
		return string


class ffmpeg:
	def __init__(self, filepath):
		self.scrubbing = True
		self.filepath = filepath
		return

	def metadata(self):
		tags = {}
		output = subprocess.Popen(["exiftool", self.filepath], stdout=subprocess.PIPE).communicate()[0]
		lines = output.split("\n")
		for line in lines:
			line = line.split(":", 1)
			if len(line) == 2:
				tags[line[0].strip()] = line[1].strip()
		return tags

	def scrub(self):
		tmp_name = "./metascrub_tmp." + self.filepath.split(".")[-1]
		output = subprocess.Popen(["ffmpeg", "-i", self.filepath, "-map_metadata", "-1", "-c:v", "copy", "-c:a", "copy", tmp_name], stdout=subprocess.PIPE).communicate()[0]
		f = open(tmp_name, "rb")
		string = f.read()
		f.close()
		os.remove(tmp_name)
		return string


class pdf:
	def __init__(self, filepath):
		self.scrubbing = True
		self.pdf = pyPdf.PdfFileReader(open(filepath, "rb"))
		return

	def metadata(self):
		output = {}
		metadata = self.pdf.getDocumentInfo()
		for key, value in metadata.items():
			if isinstance(value, pyPdf.generic.TextStringObject):
				output[key[1:]] = value
			elif isinstance(value, pyPdf.generic.IndirectObject):
				output[key[1:]] = self._find(key, self.pdf.resolvedObjects)
		return output

	def _find(self, needle, haystack):
		for key in haystack.keys():
			try:
				value = haystack[key]
			except:
				continue
			if key == needle:
				return value
			if type(value) == types.DictType or isinstance(value, pyPdf.generic.DictionaryObject):
				x = self._find(needle, value)
				if x is not None:
					return x

	def scrub(self):
		outputStream = StringIO.StringIO()
		output = pyPdf.PdfFileWriter()
		infoDict = output._info.getObject()
		infoDict.update({
			pyPdf.generic.NameObject('/Producer'): pyPdf.generic.createStringObject(u''),
		})
		for page in range(self.pdf.getNumPages()):
			output.addPage(self.pdf.getPage(page))
		output.write(outputStream)
		string = outputStream.getvalue()
		outputStream.close()
		return string


class openxml:
	def __init__(self, filepath):
		self.scrubbing = False
		self.filepath = filepath
		return

	def metadata(self):
		output = {}
		doc = openxmllib.openXmlDocument(path=self.filepath)
		for key, value in doc.coreProperties.items():
			output[key] = value
		for key, value in doc.extendedProperties.items():
			output[key] = value
		return output

	def scrub(self):
		return False


if __name__ == "__main__":
	banner = "\n -  -- ---=[  Metafiend (pdf, exif, openxml, etc.)  ]=--- --  - \n"
	usage = "usage: %prog [options] <INPUT FILE>"
	version = "%prog " + str(VERSION)
	parser = OptionParser(usage=usage, version=version)
	parser.add_option("-d", "--directory",
		action="store",
		dest="directory",
		default=False,
		help="Process an entire directory. <INPUT FILE> not needed.")
	parser.add_option("-o", "--output",
		action="store",
		dest="output",
		default=False,
		help="Output filename or directory (directory mode)",
		metavar="filename.pdf")
	debug = OptionGroup(parser, "Debug Options")
	debug.add_option("-q", "--quiet",
		action="store_true",
		dest="quiet",
		default=False,
		help="Quiet some output")

	parser.add_option_group(debug)

	(options, args) = parser.parse_args()

	if (len(args) < 1 and not options.directory):
		print banner
		parser.print_help()
		print ""
		sys.exit()

	if not options.quiet:
		print banner

	if options.directory:
		print "Processing directory '%s':" % (options.directory)
		files = os.listdir(options.directory)
		for filepath in files:
			if not os.path.isdir(filepath):
				print "Processing '%s' ... " % (filepath)
				document = autoclass(options.directory + "/" + filepath)
				if not document:
					print "ERROR: Document type is unsupported"
				else:
					metadata = document.metadata()
					if metadata:
						for key, value in metadata.items():
							print " - %s: %s" % (key, value)
					if options.output:
						print "Scrubbing document ... ",
						if not document or not document.scrubbing:
							print "ERROR: Scrubbing is not supported with this document type!"
						else:
							output_filepath = options.output + "/scrubbed_" + os.path.split(document.filepath)[1]
							output = file(output_filepath, 'wb')
							output.write(document.scrub())
							output.close()
							print "%s" % (output_filepath)
	else:
		options.input = args[0]
		document = autoclass(options.input)
		if not document:
			print "ERROR: File format is not supported!"
			sys.exit(1)
		if not options.quiet:
			print "Reading metadata from input \"%s\":" % (options.input)
		metadata = document.metadata()
		if metadata:
			for key, value in metadata.items():
				print " - %s: %s" % (key, value)
		if options.output:
			if not document.scrubbing:
				print "\nERROR: Scrubbing is not supported with this document type!"
				sys.exit(1)
			else:
				if not options.quiet:
					print "\nWriting scrubbed output file \"%s\" ..." % (options.output),
				output = file(options.output, 'wb')
				output.write(document.scrub())
				output.close()
				if not options.quiet:
					print "Done"
				if not options.quiet:
					print "\nReading metadata from output \"%s\":" % (options.output)
				metadata = autoclass(options.output).metadata()
				if metadata:
					for key, value in metadata.items():
						print " - %s: %s" % (key, value)
	if not options.quiet:
		print ""
