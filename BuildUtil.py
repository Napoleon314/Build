import os, sys, re, multiprocessing, subprocess, shutil, platform, time

def GetLinuxName():
  if os.path.isfile("/etc/os-release"):
    desc = {}
    for line in os.popen("cat /etc/os-release").read().split("\n"):
      pair = line.split("=")
      if len(pair) != 2: continue
      desc[pair[0].lower()] = pair[1].replace("\"", "").replace("'", "")
    if "id" in desc and "version_id" in desc:
      ret = "%s_%s" % (desc["id"].capitalize(), desc["version_id"].replace(".", "_"))
      return ret
  if os.path.isfile("/etc/os-release"):
    desc = os.popen("cat /etc/issue").read()
    name_id = desc.split(" ")[0]
    ver = re.findall(r"\d+\.\d+", desc)
    if len(ver) > 0:
      ret = "%s_%s" % (name_id.capitalize(), ver[0].replace(".", "_"))
      return ret
  return "Linux"

def LogError(message):
  print("[E] %s" % message)
  sys.stdout.flush()
  if 0 == sys.platform.find("win"):
    pause_cmd = "pause"
  else:
    pause_cmd = "read"
  subprocess.call(pause_cmd, shell = True)
  sys.exit(1)

def LogInfo(message):
  print("[I] %s" % message)
  sys.stdout.flush()

def LogWarning(message):
  print("[W] %s" % message)
  sys.stdout.flush()

def GetMaxVersion(path):
  dirs = os.listdir(path)
  ret = []
  ret_dir = None
  for dir in dirs:
    if not re.match(r"(\d+\.)*\d+", dir): continue
    if ret:
      cur = dir.split(".")
      for i in range(max(len(ret), len(cur))):
        if i < len(ret): n1 = int(ret[i])
        else: n1 = 0
        if i < len(cur): n2 = int(cur[i])
        else: n2 = 0
        if n2 > n1:
          ret = cur
          ret_dir = dir
          break
        elif n2 < n1:
          break
      continue
    else:
      ret = dir.split(".")
      ret_dir = dir
  return ret_dir

def LoadConfig(config, default_config):
  if not os.path.isfile(config):
    if not os.path.isfile(default_config): return
    print("Generating %s ..." % config)
    sys.stdout.flush()
    shutil.copyfile(default_config, config)
  if not os.path.isfile(config): return
  config_content = {}
  exec(open(config).read(), config_content)
  ret_config = {}
  for key in config_content:
    if "__builtins__" == key: continue
    os.environ[key.upper()] = config_content[key]
    ret_config[key.upper()] = config_content[key]
  return ret_config

def EnsureDirectory(dir, is_clean = False, is_make = True):
  if os.path.isfile(dir): os.remove(dir)
  if is_clean and os.path.isdir(dir):
    try:
      shutil.rmtree(dir)
      if(is_make): os.makedirs(dir)
    except:
      for sub in os.listdir(dir):
        sub_path = "%s/%s" % (dir, sub)
        if os.path.isfile(sub_path):
          os.remove(sub_path)
        elif os.path.isdir(sub_path):
          shutil.rmtree(sub_path)
  elif not os.path.exists(dir):
    if(is_make): os.makedirs(dir)

def IsFileModified(dst, src):
  if not os.path.isfile(src): LogError("\"%s\" does not exist" % src)
  if not os.path.isfile(dst): return True
  return os.stat(src).st_mtime > os.stat(dst).st_mtime

class Solution:
  def __init__(self, path):
    self.configs = {}
    exec(open(path).read(), self.configs)
    self.path = os.path.abspath(path)

  def GetConfig(self, key, default):
    if not key in self.configs:
      return default
    return self.configs[key]

  def GetName(self):
    return self.GetConfig("name", self.path.replace("\\", "/").split("/")[-2])

  def GetCMakeMinVer(self):
    return self.GetConfig("cmake_min_ver", "3.9")

  def GetProjects(self):
    return self.GetConfig("projects", [])

  def GenCMake(self, dir, is_clean):
    cmake_dir = "%s/cmake" % dir
    EnsureDirectory(cmake_dir, is_clean)
    cmake_file = os.path.abspath("%s/CMakeLists.txt" % cmake_dir)
    if not IsFileModified(cmake_file, self.path) and not is_clean: return
    with open(cmake_file, "w", encoding="utf-8") as file:
      LogInfo("Generating [%s] ...\n" % cmake_file)
      self.GenCMakeHeader(file)
      file.write("\n")
      self.GenCMakeStart(file)
      file.write("\n")
      self.GenProjects(file)

  def GenCMakeHeader(self, file):
    file.write("############################################################################\n")
    file.write("##\n")
    file.write("## -------------------------------------------------------------------------\n")
    file.write("##  Solution:    %s\n" % self.GetName())
    file.write("##  Generated:   %s by VenusBuild\n" % time.strftime("%Y/%m/%d %H:%M", time.localtime()))
    file.write("## -------------------------------------------------------------------------\n")
    file.write("##\n")
    file.write("############################################################################\n")

  def GenCMakeStart(self, file):
    file.write("CMAKE_MINIMUM_REQUIRED(VERSION %s)\n" % self.GetCMakeMinVer())
    file.write("\n")
    file.write("PROJECT(%s)\n" % self.GetName())
    file.write("\n")
    file.write("FILE(TO_CMAKE_PATH $ENV{VENUS_BUILD_PATH} VENUS_BUILD_PATH)\n")
    file.write("LIST(APPEND CMAKE_MODULE_PATH ${VENUS_BUILD_PATH}/cmake)\n")
    file.write("INCLUDE(VenusBuild)\n")

  def GenProjects(self, file):
    projects = self.GetProjects()
    first = True
    for group in projects:
      if first: first = False
      else: file.write("\n")
      self.GenGroupProjects(file, group, projects[group])

  def GenGroupProjects(self, file, group, projs):
    file.write("IF((NOT DEFINED ENV{NO_%s}) OR (NOT $ENV{NO_%s}))\n" % (group.upper(), group.upper()))
    tab = "  "
    file.write("%sSET(BUILD_GROUP \"%s\")\n" % (tab, group))
    for name in projs:
      file.write("\n")
      self.GenProject(file, tab, group, name, projs[name])
    file.write("ENDIF()\n")

  def GenProject(self, file, tab, group, name, proj):
    if isinstance(proj, str):
      proj_type = proj.lower()
      proj = {}
    if "version" in proj:
      file.write("%sSET(%s \"%s\")\n"
        % (tab, ("%s_version" % name).upper(), proj["version"]))
    proj_path = "%s/%s" % (group, name)
    if "path" in proj: proj_path = proj["path"]
    proj_cmake = "%s/%s.cmake" % (proj_path, name)
    if os.path.isfile("%s/%s" % (os.path.dirname(self.path), proj_cmake)):
      file.write("%sINCLUDE(../../%s)\n" % (tab, proj_cmake))
    else:
      if "type" in proj:
        proj_type = proj["type"].lower()
      if proj_type == "lib":
        file.write("%sADD_LIB(\"%s\" \"%s\" %s %s %s false)\n"
          % (tab, group, name
          , self.GetProjList(proj, "defs")
          , self.GetProjList(proj, "incs")
          , self.GetProjList(proj, "libs")))
      elif proj_type == "venus3d_app":
        ver = "0,0,0"
        appid = "com.venus3d.%s" % name.lower()
        win = "false"
        file.write("%sADD_VENUS3D_APP(\"%s\" \"%s\" \"%s\" \"%s\")\n"
          % (tab, name, ver, appid, win))
      elif proj_type == "unity_venus3d_plugin":
        file.write("%sADD_UNITY_VENUS3D_PLUGIN(\"%s\" \"%s\" \"../../../Include\")\n"
          % (tab, group, name))
      else: return
      if "pch" in proj and isinstance(proj["pch"], str):
        file.write("%sADD_PRECOMPILED_HEADER(\"%s\" \"%s\")\n"
          % (tab, name, proj["pch"]))
      if "wd" in proj:
        file.write("%sDISABLE_WARNINGS(\"%s\" %s)\n"
          % (tab, name, self.GetProjList(proj, "wd")))

  def GetProjList(self, proj, tag):
    ret = "\""
    if tag in proj:
      if isinstance(proj[tag], str):
        ret += proj[tag]
      elif isinstance(proj[tag], list):
        first = True
        for val in proj[tag]:
          if not isinstance(val, str): continue
          if first: first = False
          else: ret += ";"
          ret += val
    ret += "\""
    return ret

  def GetGenerates(self):
    ret = []
    projects = self.GetProjects()
    for group in projects:
      group_projs = projects[group]
      for name in group_projs:
        proj = group_projs[name]
        gen_proj_path = self.GetGenerate(group, name, proj)
        if gen_proj_path: ret.append(gen_proj_path)
    return ret

  def GetGenerate(self, group, name, proj):
    proj_path = "%s/%s" % (group, name)
    if "path" in proj: proj_path = proj["path"]
    proj_path = os.path.abspath("%s/%s" % (os.path.dirname(self.path), proj_path))
    if not os.path.isfile("%s/CMakeLists.txt" % proj_path): return None
    option = " -DBUILD_GROUP=\"%s\"" % group
    if "version" in proj:
      option += " -D%s_VERSION=\"%s\"" % (name.upper(), proj["version"])
    return [name, proj_path, option]

def ListSolutionFiles(solution, path = "."):
  res = []
  path = os.path.abspath(path)
  for sub in solution.split("|"):
    sub_path = "%s/%s" % (path, sub)
    if os.path.isdir(sub_path):
      cfg_path = "%s/solution.py" % sub_path
      if os.path.exists(cfg_path):
        res.append(Solution(cfg_path))
  return res

class CompilerInfo:
  def __init__(self, build_info, arch, gen_name, compiler_root, vcvarsall_path = "", vcvarsall_options = ""):
    self.arch = arch
    self.generator = gen_name
    self.compiler_root = compiler_root
    self.vcvarsall_path = vcvarsall_path
    self.vcvarsall_options = vcvarsall_options

    self.is_cross_compiling = build_info.is_cross_compiling
    if build_info.host_arch != arch:
      self.is_cross_compiling = True

class BatchCommand:
  def __init__(self, task_name, environ = None):
    self.task_name_ = task_name
    self.commands_ = []
    host_platform = sys.platform
    if 0 == host_platform.find("win"):
      host_platform = "win"
    elif 0 == host_platform.find("linux"):
      host_platform = "linux"
    elif 0 == host_platform.find("darwin"):
      host_platform = "darwin"
    self.host_platform_ = host_platform
    if "win" == self.host_platform_:
      self.commands_.append("@echo off")
    if environ: self.AddEnviron(environ)

  def AddCommand(self, cmd):
    self.commands_ += [cmd]

  def AddPythonCommand(self, file, args = []):
    if "win" == self.host_platform_:
      python_cmd = "python"
    else:
      python_cmd = "python3"
    cmd = "%s %s.py" % (python_cmd, file)
    for arg in args:
      cmd += " %s" % arg
    self.commands_ += [cmd]

  def AddEnviron(self, environ):
    for key in environ:
      if "win" == self.host_platform_:
        self.AddCommand("@SET %s=%s" % (key, environ[key]))
      else:
        self.AddCommand("export %s=%s" % (key, environ[key]))

  def Execute(self):
    batch_file = "ve_build."
    if "win" == self.host_platform_:
      batch_file += "bat"
    else:
      batch_file += "sh"
    batch_f = open(batch_file, "w")
    batch_f.writelines([cmd_line + "\n" for cmd_line in self.commands_])
    batch_f.close()
    if "win" == self.host_platform_:
      ret_code = subprocess.call(batch_file, shell = True)
    else:
      subprocess.call("chmod 777 " + batch_file, shell = True)
      ret_code = subprocess.call("./" + batch_file, shell = True)
    os.remove(batch_file)
    return ret_code

  def ExecuteEx(self, repeat = 0, log_name = "", log_dir = ""):
    if log_name and len(log_name) > 0:
      log_name = "%s_%s.txt" % (log_name, time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime()))
      if log_dir and len(log_dir) > 0:
        EnsureDirectory(log_dir)
        log_name = "%s/%s" % (log_dir, log_name)
      with open(log_name, "w", encoding="utf-8") as file:
        file.writelines([cmd_line + "\n" for cmd_line in self.commands_])
    i = 1
    if self.task_name_ and len(self.task_name_) > 0:
      LogInfo("%s ...\n" % self.task_name_)
    while self.Execute() !=0:
      if i < repeat:
        LogWarning("%s failed, retry %d ...\n" % (self.task_name_, i))
        i += 1
      else:
        LogError("%s failed.\n" % self.task_name_)
    print("")
    LogInfo("%s succeeded.\n" % self.task_name_)

class BuildInfo:
  def __init__(self, env_cfgs, target = "auto", project = "auto", compiler = "auto", archs = "auto", configs = "auto", cmake_path = "auto", prefer_shared = True):
    self.env_cfgs = env_cfgs
    env = os.environ
    host_platform = sys.platform
    if 0 == host_platform.find("win"):
      host_platform = "win"
      self.host_platform_type = "windows"
      self.host_platform_name = "Windows"
    elif 0 == host_platform.find("linux"):
      host_platform = "linux"
      self.host_platform_type = "linux"
      self.host_platform_name = GetLinuxName()
      # self.linux_description = os.popen("cat /etc/issue").read()
      # self.linux_distributor = self.linux_description.split(" ")[0]
      # ver = re.findall(r"\d+\.\d+", self.linux_description)
      # if len(ver) <= 0:
      #   LogError("Unknown linux release")
      # self.linux_release = ver[0]
      # self.host_platform_name = "%s_%s" % (self.linux_distributor, self.linux_release.replace(".", "_"))
    elif 0 == host_platform.find("darwin"):
      host_platform = "darwin"
      self.host_platform_type = "darwin"
      self.host_platform_name = "Darwin"
    if "auto" == target:
      target_platform = host_platform
    else:
      target_platform = target.lower()
      if 0 == target_platform.find("android"):
        if "ANDROID_NDK" in env:
          self.is_android_studio = False
        elif "ANDROID_SDK" in env:
          self.is_android_studio = True
        elif not self.FindAndroid():
          LogError("You must define an \"ANDROID_NDK\" or an \"ANDROID_SDK\" environment variable to your location of NDK or ADK.\n")
        space_place = target_platform.find(' ')
        if space_place != -1:
          android_ver = target_platform[space_place + 1:]
          target_platform = target_platform[0:space_place]
          if "9.0" == android_ver:
            target_api_level = 28
          elif "8.1" == android_ver:
            target_api_level = 27
          elif "8.0" == android_ver:
            target_api_level = 26
          elif "7.1" == android_ver:
            target_api_level = 25
          elif "7.0" == android_ver:
            target_api_level = 24
          elif "6.0" == android_ver:
            target_api_level = 23
          elif "5.1" == android_ver:
            target_api_level = 22
          elif "5.0" == android_ver:
            target_api_level = 21
          else:
            LogError("Unsupported Android version.\n")
        else:
          target_api_level = 21
        self.target_api_level = target_api_level
      elif "ios" == target_platform.lower() and "darwin" == host_platform:
        target_platform = "ios"
      else:
        LogError("Unsupported target platform.\n")

    self.prefer_shared = prefer_shared
    if ("android" == target_platform) or ("ios" == target_platform) or (not prefer_shared):
      self.lib_shared = False
    else:
      self.lib_shared = True

    self.host_platform = host_platform
    self.target_platform = target_platform
    self.is_cross_compiling = host_platform != target_platform

    self.host_arch = platform.machine()
    if (self.host_arch == "AMD64") or (self.host_arch == "x86_64"):
      self.host_arch = "x64"
    elif (self.host_arch == "ARM64"):
      self.host_arch = "arm64"
    else:
      LogError("Unknown host architecture %s.\n" % self.host_arch)

    if self.host_platform == "win":
      self.where_cmd = "where"
      self.sep = "\r\n"
      self.slash = "\\"
    else:
      self.where_cmd = "which"
      self.sep = "\n"
      self.slash = "/"

    self.cmake_path = cmake_path
    if self.cmake_path == "auto":
      self.cmake_path = self.FindCMake()
    self.cmake_ver = self.RetrieveCMakeVersion()
    if self.cmake_ver < 39:
      LogError("CMake 3.9+ is required.")

    self.is_windows_desktop = False
    self.is_windows = False
    self.is_android = False
    self.is_linux = False
    self.is_darwin = False
    self.is_ios = False

    if "win" == target_platform:
      self.is_windows = True
      self.is_windows_desktop = True
    elif "linux" == target_platform:
      self.is_linux = True
    elif "darwin" == target_platform:
      self.is_darwin = True
    elif "ios" == target_platform:
      self.is_ios = True
      self.target_platform_name = "iOS"
    elif "android" == target_platform:
      self.is_android = True
      self.target_platform_name = "Android"
      if self.is_android_studio:
        ndk_path = "%s/ndk" % env["ANDROID_SDK"]
        ndk_ver = GetMaxVersion(ndk_path)
        if not ndk_ver:
          LogError("NDK not found.")
        self.android_ndk_path = "%s/%s" % (ndk_path, ndk_ver)
      else:
        self.android_ndk_path = env["ANDROID_NDK"]

    self.is_dev_platform = (self.is_windows_desktop or self.is_linux or self.is_darwin)
    if self.is_dev_platform: self.target_platform_name = self.host_platform_name

    project_type = ""
    compiler_type = ""

    if ("auto" == project) and ("auto" == compiler):
      if 0 == target_platform.find("win"):
        program_files_folder = self.FindProgramFilesFolder()

        if len(self.FindVS2019Folder(program_files_folder)) > 0:
          project_type = "vs2019"
          compiler = "vc142"
        elif len(self.FindVS2017Folder(program_files_folder)) > 0:
          project_type = "vs2017"
          compiler = "vc141"
        elif 0 == len(compiler):
          if ("VS140COMNTOOLS" in env) or os.path.exists(program_files_folder + "\\Microsoft Visual Studio 14.0\\VC\\VCVARSALL.BAT"):
            project_type = "vs2015"
            compiler_type = "vc140"
          elif len(self.FindClang()) != 0:
            project_type = "make"
            compiler_type = "clang"
          elif len(self.FindGCC()) != 0:
            project_type = "make"
            compiler_type = "mingw"
      elif ("linux" == target_platform):
        project_type = "make"
        compiler_type = "gcc"
      elif ("android" == target_platform):
        if self.is_android_studio:
          project_type = "ninja"
        else:
          project_type = "make"
        compiler_type = "clang"
      elif ("darwin" == target_platform) or ("ios" == target_platform):
        project_type = "xcode"
        compiler_type = "clang"
      else:
        LogError("Unsupported target platform.\n")
    else:
      if project != "auto":
        project_type = project
      if compiler != "auto":
        compiler_type = compiler

    if (project_type != "") and (compiler_type == ""):
      if project_type == "vs2019":
        compiler = "vc142"
      elif project_type == "vs2017":
        compiler_type = "vc141"
      elif project_type == "vs2015":
        compiler_type = "vc140"
      elif project_type == "xcode":
        compiler_type = "clang"

    if 0 == target_platform.find("win"):
      program_files_folder = self.FindProgramFilesFolder()

      if "vc142" == compiler:
        if project_type == "vs2019":
          try_folder = self.FindVS2019Folder(program_files_folder)
          if len(try_folder) > 0:
            compiler_root = try_folder
            vcvarsall_path = "VCVARSALL.BAT"
            vcvarsall_options = ""
          else:
            LogError("Could NOT find vc142 compiler toolset for VS2019.\n")
        else:
          LogError("Could NOT find vc142 compiler.\n")
      elif "vc141" == compiler:
        if project_type == "vs2019":
          try_folder = self.FindVS2019Folder(program_files_folder)
          if len(try_folder) > 0:
            compiler_root = try_folder
            vcvarsall_path = "VCVARSALL.BAT"
            vcvarsall_options = "-vcvars_ver=14.1"
          else:
            LogError("Could NOT find vc141 compiler toolset for VS2019.\n")
        else:
          try_folder = self.FindVS2017Folder(program_files_folder)
          if len(try_folder) > 0:
            compiler_root = try_folder
            vcvarsall_path = "VCVARSALL.BAT"
          else:
            LogError("Could NOT find vc141 compiler.\n")
          vcvarsall_options = ""
      elif "vc140" == compiler:
        if project_type == "vs2019":
          try_folder = self.FindVS2019Folder(program_files_folder)
          if len(try_folder) > 0:
            compiler_root = try_folder
            vcvarsall_path = "VCVARSALL.BAT"
            vcvarsall_options = "-vcvars_ver=14.0"
          else:
            LogError("Could NOT find vc140 compiler toolset for VS2017.\n")
        elif project_type == "vs2017":
          try_folder = self.FindVS2017Folder(program_files_folder)
          if len(try_folder) > 0:
            compiler_root = try_folder
            vcvarsall_path = "VCVARSALL.BAT"
            vcvarsall_options = "-vcvars_ver=14.0"
          else:
            LogError("Could NOT find vc140 compiler toolset for VS2017.\n")
        else:
          if "VS140COMNTOOLS" in env:
            compiler_root = env["VS140COMNTOOLS"] + "..\\..\\VC\\bin\\"
            vcvarsall_path = "..\\VCVARSALL.BAT"
          else:
            try_folder = program_files_folder + "\\Microsoft Visual Studio 14.0\\VC\\bin\\"
            try_vcvarsall = "..\\VCVARSALL.BAT"
            if os.path.exists(try_folder + try_vcvarsall):
              compiler_root = try_folder
              vcvarsall_path = try_vcvarsall
            else:
              LogError("Could NOT find vc140 compiler.\n")
          vcvarsall_options = ""
      elif "clang" == compiler:
        clang_loc = self.FindClang()
        compiler_root = clang_loc[0:clang_loc.rfind("\\clang++") + 1]
      elif "mingw" == compiler:
        gcc_loc = self.FindGCC()
        compiler_root = gcc_loc[0:gcc_loc.rfind("\\g++") + 1]
    else:
      compiler_root = ""

    if "" == project_type:
      if "vc142" == compiler:
        project_type = "vs2019"
      if "vc141" == compiler:
        project_type = "vs2017"
      elif "vc140" == compiler:
        project_type = "vs2015"
      elif ("clang" == compiler) and (("darwin" == target_platform) or ("ios" == target_platform)):
        project_type = "xcode"
      elif ("android" == target_platform and self.is_android_studio):
        project_type = "ninja"
      else:
        project_type = "make"

    if "" == archs or "auto" == archs:
      if self.is_android or self.is_ios:
        archs = "arm64"
      else:
        archs = "x64"
    elif "all" == archs:
      if self.is_android:
        archs = "arm64|arm32|x64|x86"
      elif self.is_ios:
        archs = "arm64|x64"
      else:
        archs = "x64"

    archs = archs.split('|')
    for i in range(len(archs)):
      if "arm" == archs[i]:
        archs[i] = "arm32"

    if "" == configs or "auto" == configs:
      cfg = "Debug|Release"
    elif "all" == configs:
      cfg = "Debug|Release|MinSizeRel|RelWithDebInfo"
    else:
      cfg = configs

    cfg = cfg.split('|')

    multi_config = False
    compilers = []

    if "vs2019" == project_type:
      self.vs_version = 16
      if "vc142" == compiler:
        compiler_name = "vc"
        compiler_version = 142
      elif "vc141" == compiler:
        compiler_name = "vc"
        compiler_version = 141
      elif "vc140" == compiler:
        compiler_name = "vc"
        compiler_version = 140
      else:
        LogError("Wrong combination of project %s and compiler %s.\n" % (project_type, compiler))
      multi_config = True
      for arch in archs:
        compilers.append(CompilerInfo(self, arch, "Visual Studio 16", compiler_root, vcvarsall_path, vcvarsall_options))
    elif "vs2017" == project_type:
      self.vs_version = 15
      if "vc141" == compiler:
        compiler_name = "vc"
        compiler_version = 141
      elif "vc140" == compiler:
        compiler_name = "vc"
        compiler_version = 140
      else:
        LogError("Wrong combination of project %s and compiler %s.\n" % (project_type, compiler))
      multi_config = True
      for arch in archs:
        compilers.append(CompilerInfo(self, arch, "Visual Studio 15", compiler_root, vcvarsall_path, vcvarsall_options))
    elif "vs2015" == project_type:
      self.vs_version = 14
      if "vc140" == compiler_type:
        compiler_name = "vc"
        compiler_version = 140
      else:
        LogError("Wrong combination of project %s and compiler %s.\n" % (project_type, compiler))
      multi_config = True
      for arch in archs:
        compilers.append(CompilerInfo(self, arch, "Visual Studio 14", compiler_root, vcvarsall_path, vcvarsall_options))
    elif "xcode" == project_type:
      if "clang" == compiler_type:
        compiler_name = "clang"
        compiler_version = self.RetrieveClangVersion()
        gen_name = "Xcode"
        multi_config = True
        for arch in archs:
          compilers.append(CompilerInfo(self, arch, gen_name, compiler_root))
      else:
        LogError("Wrong combination of project %s and compiler %s.\n" % (project_type, compiler))
    elif "make" == project_type or "ninja" == project_type:
      if "ninja" == project_type:
        gen_name = "Ninja"
      else:
        if "win" == host_platform:
          gen_name = "MinGW Makefiles"
        else:
          gen_name = "Unix Makefiles"
      if "clang" == compiler_type:
        compiler_name = "clang"
        compiler_version = self.RetrieveClangVersion()
        for arch in archs:
          compilers.append(CompilerInfo(self, arch, gen_name, compiler_root))
      elif "mingw" == compiler_type:
        compiler_name = "mgw"
        compiler_version = self.RetrieveGCCVersion()
        for arch in archs:
          compilers.append(CompilerInfo(self, arch, gen_name, compiler_root))
      elif "gcc" == compiler_type:
        compiler_name = "gcc"
        compiler_version = self.RetrieveGCCVersion()
        for arch in archs:
          compilers.append(CompilerInfo(self, arch, gen_name, compiler_root))
      elif "vc142" == compiler_type:
        compiler_name = "vc"
        compiler_version = 142
        for arch in archs:
          compilers.append(CompilerInfo(self, arch, gen_name, compiler_root, vcvarsall_path, vcvarsall_options))
      elif "vc141" == compiler_type:
        compiler_name = "vc"
        compiler_version = 141
        for arch in archs:
          compilers.append(CompilerInfo(self, arch, gen_name, compiler_root, vcvarsall_path, vcvarsall_options))
      elif "vc140" == compiler_type:
        compiler_name = "vc"
        compiler_version = 140
        for arch in archs:
          compilers.append(CompilerInfo(self, arch, gen_name, compiler_root, vcvarsall_path, vcvarsall_options))
      else:
        LogError("Wrong combination of project %s and compiler %s.\n" % (project_type, compiler_type))
    else:
      compiler_name = ""
      compiler_version = 0
      LogError("Unsupported compiler.\n")

    if 0 == project_type.find("vs"):
      self.proj_ext_name = "vcxproj"

    self.project_type = project_type
    self.compiler_name = compiler_name
    self.compiler_version = compiler_version
    self.multi_config = multi_config
    self.compilers = compilers
    self.archs = archs
    self.cfg = cfg

    self.jobs = multiprocessing.cpu_count()

    self.DisplayInfo()

  def MSBuildAddBuildCommand(self, batch_cmd, sln_name, proj_name, config, arch = ""):
    batch_cmd.AddCommand('@SET VisualStudioVersion=%d.0' % self.vs_version)
    if len(proj_name) != 0:
      file_name = "%s.%s" % (proj_name, self.proj_ext_name)
    else:
      file_name = "%s.sln" % sln_name
    config_str = "Configuration=%s" % config
    if len(arch) != 0:
      config_str = "%s,Platform=%s" % (config_str, arch)
    batch_cmd.AddCommand('@MSBuild %s /nologo /m:%d /v:m /p:%s' % (file_name, self.jobs, config_str))
    batch_cmd.AddCommand('@if ERRORLEVEL 1 exit /B 1')

  def XCodeBuildAddBuildCommand(self, batch_cmd, target_name, config):
    batch_cmd.AddCommand('xcodebuild -target %s -jobs %d -configuration %s | xcpretty' % (target_name, self.jobs, config))
    batch_cmd.AddCommand('if (($? != 0)); then exit 1; fi')

  def MakeAddBuildCommand(self, batch_cmd, make_name, target):
    make_options = "-j%d" % self.jobs
    if target != "ALL_BUILD":
      make_options += " %s" % target
    if "win" == self.host_platform:
      batch_cmd.AddCommand("@%s %s" % (make_name, make_options))
      batch_cmd.AddCommand('@if ERRORLEVEL 1 exit /B 1')
    else:
      batch_cmd.AddCommand("%s %s" % (make_name, make_options))
      batch_cmd.AddCommand('if [ $? -ne 0 ]; then exit 1; fi')

  def FindAndroid(self):
    android_sdk_path = []
    android_ndk_path = []
    if 0 == sys.platform.find("win"):
      android_sdk_path.append("%s\\AppData\\Local\\Android\\sdk" % os.path.expanduser("~"))
      android_ndk_path.append("%s\\AppData\\Local\\Android\\android-ndk-r16b" % os.path.expanduser("~"))
    elif 0 == sys.platform.find("darwin"):
      android_sdk_path.append("%s/Library/Android/sdk" % os.path.expanduser("~"))
      android_ndk_path.append("%s/Library/Android/android-ndk-r16b" % os.path.expanduser("~"))
    else:
      android_ndk_path.append("/usr/local/android-ndk")
    for dir in android_sdk_path:
      if not os.path.isdir("%s/ndk" % dir): continue
      if not os.path.isdir("%s/cmake" % dir): continue
      os.environ["ANDROID_SDK"] = dir
      self.env_cfgs["ANDROID_SDK"] = dir
      self.is_android_studio = True
      return True
    for dir in android_ndk_path:
      if not os.path.isdir(dir): continue
      os.environ["ANDROID_NDK"] = dir
      self.env_cfgs["ANDROID_NDK"] = dir
      self.is_android_studio = False
      return True
    return False

  def FindGCC(self):
    if self.host_platform != "win":
      env = os.environ
      if "CXX" in env:
        gcc_loc = env["CXX"]
        if len(gcc_loc) != 0:
          return gcc_loc.split(self.sep)[0]

    gcc_loc = subprocess.check_output(self.where_cmd + " g++", shell = True).decode()
    if len(gcc_loc) == 0:
      LogError("Could NOT find g++. Please install g++ 7.1+, set its path into CXX, or put its path into %%PATH%%.")
    return gcc_loc.split(self.sep)[0]

  def RetrieveGCCVersion(self):
    gcc_ver = subprocess.check_output([self.FindGCC(), "-dumpfullversion"]).decode()
    gcc_ver_components = gcc_ver.split(".")
    return int(gcc_ver_components[0] + gcc_ver_components[1])

  def FindClang(self):
    if self.host_platform != "win":
      env = os.environ
      if "CXX" in env:
        clang_loc = env["CXX"]
        if len(clang_loc) != 0:
          return clang_loc.split(self.sep)[0]

    clang_loc = subprocess.check_output(self.where_cmd + " clang++", shell = True).decode()
    if len(clang_loc) == 0:
      LogError("Could NOT find g++. Please install clang++ 3.6+, set its path into CXX, or put its path into %%PATH%%.")
    return clang_loc.split(self.sep)[0]

  def RetrieveClangVersion(self, path = ""):
    if ("android" == self.target_platform):
      platform_path = self.host_platform_type
      if self.host_arch == "x64": platform_path += "-x86_64"
      prebuilt_llvm_path = self.android_ndk_path + self.slash + "toolchains" + self.slash + "llvm"
      prebuilt_clang_path = prebuilt_llvm_path + self.slash + "prebuilt" + self.slash + platform_path + self.slash + "bin"
      clang_path = prebuilt_clang_path + self.slash + "clang"
    else:
      clang_path = path + "clang"
    clang_ver = subprocess.check_output([clang_path, "--version"]).decode()
    clang_ver_tokens = clang_ver.split()
    for i in range(0, len(clang_ver_tokens)):
      if "version" == clang_ver_tokens[i]:
        clang_ver_components = clang_ver_tokens[i + 1].split(".")
        break
    return int(clang_ver_components[0] + clang_ver_components[1])

  def FindVS2017ClangC2(self, folder):
    found = False
    compiler_root = ""
    vcvarsall_path = ""
    if os.path.exists(folder + "Microsoft.ClangC2Version.default.txt"):
      version_file = open(folder + "Microsoft.ClangC2Version.default.txt")
      version = version_file.read().strip()
      compiler_root = "%s\\..\\..\\Tools\\ClangC2\\%s\\bin\\HostX86\\" % (folder, version)
      vcvarsall_path = "..\\..\\..\\..\\..\\Auxiliary\\Build\\VCVARSALL.BAT"
      found = True
      version_file.close()
    return (found, compiler_root, vcvarsall_path)

  def FindProgramFilesFolder(self):
    env = os.environ
    if "AMD64" == platform.machine():
      if "ProgramFiles(x86)" in env:
        program_files_folder = env["ProgramFiles(x86)"]
      else:
        program_files_folder = "C:\\Program Files (x86)"
    else:
      if "ProgramFiles" in env:
        program_files_folder = env["ProgramFiles"]
      else:
        program_files_folder = "C:\\Program Files"
    return program_files_folder

  def FindVS2019Folder(self, program_files_folder):
    return self.FindVS2017PlusFolder(program_files_folder, 16, "2019")

  def FindVS2017Folder(self, program_files_folder):
    return self.FindVS2017PlusFolder(program_files_folder, 15, "2017")

  def FindVS2017PlusFolder(self, program_files_folder, vs_version, vs_name):
    try_vswhere_location = program_files_folder + "\\Microsoft Visual Studio\\Installer\\vswhere.exe"
    if os.path.exists(try_vswhere_location):
      vs_location = subprocess.check_output([try_vswhere_location,
        "-products", "*",
        "-latest",
        "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "-property", "installationPath",
        "-version", "[%d.0,%d.0)" % (vs_version, vs_version + 1),
        "-prerelease"]).decode().split("\r\n")[0]
      try_folder = vs_location + "\\VC\\Auxiliary\\Build\\"
      try_vcvarsall = "VCVARSALL.BAT"
      if os.path.exists(try_folder + try_vcvarsall):
        return try_folder
    else:
      names = ("Preview", vs_name)
      skus = ("Community", "Professional", "Enterprise", "BuildTools")
      for name in names:
        for sku in skus:
          try_folder = program_files_folder + "\\Microsoft Visual Studio\\%s\\%s\\VC\\Auxiliary\\Build\\" % (name, sku)
          try_vcvarsall = "VCVARSALL.BAT"
          if os.path.exists(try_folder + try_vcvarsall):
            return try_folder
    return ""

  def FindCMake(self):
    if "android" == self.target_platform and self.is_android_studio:
      cmake_path = "%s/cmake" % os.environ["ANDROID_SDK"]
      ver_dir = GetMaxVersion(cmake_path)
      if not ver_dir:
        LogError("Could NOT find CMake from \"%s\"" % cmake_path)
      cmake_path = "%s/%s/bin/cmake" % (cmake_path, ver_dir)
      return cmake_path
    cmake_loc = subprocess.check_output(self.where_cmd + " cmake", shell = True).decode()
    if len(cmake_loc) == 0:
      LogError("Could NOT find CMake. Please install CMake 3.6+, set its path into CfgBuild's self.cmake_path, or put its path into %%PATH%%.")
    return cmake_loc.split(self.sep)[0]

  def RetrieveCMakeVersion(self):
    cmake_ver = subprocess.check_output([self.cmake_path, "--version"]).decode()
    if len(cmake_ver) == 0:
      LogError("Could NOT find CMake. Please install CMake 3.6+, set its path into CfgBuild's self.cmake_path, or put its path into %%PATH%%.")
    cmake_ver = cmake_ver.split()[2]
    cmake_ver_components = cmake_ver.split('.')
    return int(cmake_ver_components[0] + cmake_ver_components[1])

  def DisplayInfo(self):
    print("Build information:")
    print("\tCMake path: %s" % self.cmake_path)
    print("\tCMake version: %s" % self.cmake_ver)
    print("\tHost platform: %s" % self.host_platform_name)
    print("\tTarget platform: %s" % self.target_platform_name)
    if self.is_android:
      print("\tTarget API level: %d" % self.target_api_level)
    print("\tCPU count: %d" % self.jobs)
    print("\tUse shared library: %s" % self.lib_shared)
    print("\tProject type: %s" % self.project_type)
    print("\tCompiler: %s%d" % (self.compiler_name, self.compiler_version))
    archs = ""
    for i in range(0, len(self.compilers)):
      archs += self.compilers[i].arch
      if i != len(self.compilers) - 1:
        archs += ", "
    print("\tArchitectures: %s" % archs)
    cfgs = ""
    for i in range(0, len(self.cfg)):
      cfgs += self.cfg[i]
      if i != len(self.cfg) - 1:
        cfgs += ", "
    print("\tConfigures: %s" % cfgs)

    print("")
    sys.stdout.flush()

  def SetConfig(self, key, val):
    key = key.upper()
    if not type(val) is str:
      val = str(val)
    self.env_cfgs[key] = val

  def GetConfig(self, key, default = ""):
    key = key.upper()
    if not key in self.env_cfgs:
      self.env_cfgs[key] = default
      return default
    return self.env_cfgs[key]

  def BuildSolutions(self, solutions, is_venus3d = False, need_gen = False, need_clear = False, need_build = False, need_install = False, additional_options = ""):
    for solution in ListSolutionFiles(solutions):
      self.BuildSolution(solution, is_venus3d, need_gen, need_clear, need_build, need_install, additional_options)

  def BuildSolution(self, solution, is_venus3d = False, need_gen = False, need_clear = False, need_build = False, need_install = False, additional_options = ""):
    curdir = os.path.abspath(os.curdir)
    if is_venus3d: self.SetConfig("venus3d_path", curdir)
    self.SetConfig("need_gen", str(need_gen).upper())
    self.SetConfig("need_clear", str(need_clear).upper())
    root_path = os.path.abspath(os.path.split(solution.path)[0])
    self.SetConfig("root_path", root_path)
    binary_path = os.path.abspath("%s/%s" % (root_path, self.GetConfig("bin_dir_name", "bin")))
    self.SetConfig("binary_path", binary_path)
    build_path = os.path.abspath("%s/%s" % (root_path, self.GetConfig("build_dir_name", "build")))
    self.SetConfig("build_path", build_path)
    document_path = os.path.abspath("%s/%s" % (root_path, self.GetConfig("doc_dir_name", "doc")))
    self.SetConfig("document_path", document_path)
    inc_dir_name = self.GetConfig("inc_dir_name", "inc")
    src_dir_name = self.GetConfig("src_dir_name", "src")
    lib_dir_name = self.GetConfig("lib_dir_name", "lib")
    install_path = os.path.abspath("%s/%s" % (root_path, self.GetConfig("install_dir_name", "prefix")))
    self.SetConfig("install_path", install_path)
    venus_build_path = os.path.abspath(self.GetConfig("venus_build_path", "Build"))
    self.SetConfig("venus_build_path", venus_build_path)
    solution.GenCMake(build_path, need_clear)
    if self.prefer_shared:
      self.SetConfig("prefer_lib", "SHARED")
    else:
      self.SetConfig("prefer_lib", "STATIC")
    if self.lib_shared:
      self.SetConfig("build_lib", "SHARED")
    else:
      self.SetConfig("build_lib", "STATIC")

    toolset_name = ""
    if 0 == self.project_type.find("vs"):
      toolset_name = "-T"
      if self.compiler_name == "clangcl":
        toolset_name += " ClangCL"
      else:
        toolset_name += " v%s," % self.compiler_version
        toolset_name += "host=x64"
    elif ("android" == self.target_platform):
      toolset_name = "clang"

    for compiler_info in self.compilers:
      if self.compiler_name != "vc":
        additional_options += " -DBUILD_ARCH_NAME=\"%s\"" % compiler_info.arch
      if "android" == self.target_platform:
        android_toolchain = os.path.abspath("%s/build/cmake/android.toolchain.cmake" % self.android_ndk_path)
        if not os.path.isfile(android_toolchain):
          android_toolchain = os.path.abspath("%s/cmake/android.toolchain.cmake" % venus_build_path)
          if not os.path.isfile(android_toolchain):
            LogError("android.toolchain.cmake can not been found")
        additional_options += " -DCMAKE_TOOLCHAIN_FILE=\"%s\"" % android_toolchain
        additional_options += " -DANDROID_NATIVE_API_LEVEL=%d" % self.target_api_level
        additional_options += " -DANDROID_PLATFORM=android-%d" % self.target_api_level
      elif "darwin" == self.target_platform:
        if "x64" == compiler_info.arch:
          additional_options += " -DCMAKE_OSX_ARCHITECTURES=x86_64"
        else:
          LogError("Unsupported Darwin architecture.\n")
      elif "ios" == self.target_platform:
        ios_toolchain = os.path.abspath("%s/cmake/ios.toolchain.cmake" % venus_build_path)
        additional_options += " -DCMAKE_TOOLCHAIN_FILE=\"%s\"" % ios_toolchain
        additional_options += " -DDEPLOYMENT_TARGET=11.0"
        if "arm64" == compiler_info.arch:
          additional_options += " -DPLATFORM=OS64"
        elif "x64" == compiler_info.arch:
          additional_options += " -DPLATFORM=SIMULATOR64"
        else:
          LogError("Unsupported iOS architecture.\n")

      if 0 == self.project_type.find("vs"):
        if "x64" == compiler_info.arch:
          vc_option = "amd64"
          vc_arch = "x64"
        elif "arm32" == compiler_info.arch:
          vc_option = "amd64_arm"
          vc_arch = "ARM"
        elif "arm64" == compiler_info.arch:
          vc_option = "amd64_arm64"
          vc_arch = "ARM64"
        else:
          LogError("Unsupported VS architecture.\n")
        if len(compiler_info.vcvarsall_options) > 0:
          vc_option += " %s" % compiler_info.vcvarsall_options

      compile_info = "%s_%s_%s%d_%s" % (self.project_type, self.target_platform_name.lower(), self.compiler_name, self.compiler_version, compiler_info.arch)
      if self.lib_shared:
        compile_info += "_shared"
      self.SetConfig("compile_info", compile_info)

      if self.multi_config:
        if 0 == self.project_type.find("vs"):
          additional_options += " -A %s" % vc_arch
        if self.compiler_name == "clangcl":
          additional_options += " -DClangCL_Path=\"" + compiler_info.compiler_root + "../../Tools/Llvm/bin/\""

        for generate in solution.GetGenerates():
          gen_dir = os.path.abspath("%s/gen_%s/%s" % (build_path,  compile_info, generate[0]))
          EnsureDirectory(gen_dir, need_clear)
          os.chdir(gen_dir)
          gen_cmd = BatchCommand("Generate %s" % generate[0], self.env_cfgs)
          gen_cmd.AddCommand("\"%s\" -G \"%s\" %s %s %s \"%s\"" % (self.cmake_path, compiler_info.generator, toolset_name, additional_options, generate[2], generate[1]))
          gen_cmd.ExecuteEx(0, "gen_%s" % generate[0], "Logs")

        build_dir = os.path.abspath("%s/%s" % (build_path, compile_info))
        EnsureDirectory(build_dir, need_clear)
        EnsureDirectory(binary_path, need_clear, False)
        os.chdir(build_dir)
        cmake_cmd = BatchCommand("CMake %s" % solution.GetName(), self.env_cfgs)
        new_path = sys.exec_prefix
        if len(compiler_info.compiler_root) > 0:
          new_path += ";" + compiler_info.compiler_root
        if "win" == self.host_platform:
          cmake_cmd.AddCommand('@SET PATH=%s;%%PATH%%' % new_path)
          if 0 == self.project_type.find("vs"):
            cmake_cmd.AddCommand('@CALL "%s%s" %s' % (compiler_info.compiler_root, compiler_info.vcvarsall_path, vc_option))
            cmake_cmd.AddCommand('@CD /d "%s"' % build_dir)
        else:
          cmake_cmd.AddCommand('export PATH=$PATH:%s' % new_path)

        cmake_cmd.AddCommand('"%s" -G "%s" %s %s ../cmake' % (self.cmake_path, compiler_info.generator, toolset_name, additional_options))
        cmake_cmd.ExecuteEx(0, "cmake_%s" % solution.GetName().lower(), "Logs")

        if need_build:
          build_cmd = BatchCommand("Build %s" % solution.GetName(), self.env_cfgs)
          if 0 == self.project_type.find("vs"):
            build_cmd.AddCommand('@CALL "%s%s" %s' % (compiler_info.compiler_root, compiler_info.vcvarsall_path, vc_option))
            build_cmd.AddCommand('@CD /d "%s"' % build_dir)
          for config in self.cfg:
            if 0 == self.project_type.find("vs"):
              self.MSBuildAddBuildCommand(build_cmd, solution.GetName(), "ALL_BUILD", config, vc_arch)
            elif "xcode" == self.project_type:
              self.XCodeBuildAddBuildCommand(build_cmd, "ALL_BUILD", config)
          build_cmd.ExecuteEx(3, "build_%s" % solution.GetName().lower(), "Logs")

        if need_install:
          install_cmd = BatchCommand("Install %s" % solution.GetName(), self.env_cfgs)
          if 0 == self.project_type.find("vs"):
            install_cmd.AddCommand('@CALL "%s%s" %s' % (compiler_info.compiler_root, compiler_info.vcvarsall_path, vc_option))
            install_cmd.AddCommand('@CD /d "%s"' % build_dir)
          for config in self.cfg:
            if 0 == self.project_type.find("vs"):
              self.MSBuildAddBuildCommand(install_cmd, solution.GetName(), "INSTALL", config, vc_arch)
            elif "xcode" == self.project_type:
              self.XCodeBuildAddBuildCommand(install_cmd, "install", config)
          install_cmd.ExecuteEx(0, "install_%s" % solution.GetName().lower(), "Logs")

        os.chdir(curdir)
        sys.stdout.flush()
      else:
        if self.project_type == "ninja":
          if "android" == self.target_platform:
            make_name = "%s/ninja" % os.path.split(self.cmake_path)[0]
          else:
            make_name = "ninja"
        else:
          if "win" == self.host_platform:
            if self.target_platform == "android":
              prebuilt_make_path = self.android_ndk_path + "\\prebuilt\\windows"
              if not os.path.isdir(prebuilt_make_path):
                prebuilt_make_path = self.android_ndk_path + "\\prebuilt\\windows-x86_64"
              make_name = prebuilt_make_path + "\\bin\\make.exe"
            else:
              make_name = "mingw32-make.exe"
          else:
            make_name = "make"

        super_options = additional_options
        first = True
        for config in self.cfg:
          additional_options = super_options
          if self.target_platform == "android":
            additional_options += " -DCMAKE_MAKE_PROGRAM=\"%s\"" % make_name
          elif "clang" == self.compiler_name:
            env = os.environ
            if not ("CC" in env):
              additional_options += " -DCMAKE_C_COMPILER=clang"
            if not ("CXX" in env):
              additional_options += " -DCMAKE_CXX_COMPILER=clang++"

          additional_options += " -DCMAKE_BUILD_TYPE=\"%s\"" % config
          if "android" == self.target_platform:
            if "x86" == compiler_info.arch:
              abi_arch = "x86"
              toolchain_arch = "i686-linux-android"
            elif "x64" == compiler_info.arch:
              abi_arch = "x86_64"
              toolchain_arch = "x86_64-linux-android"
            elif "arm32" == compiler_info.arch:
              abi_arch = "armeabi-v7a"
              toolchain_arch = "arm-linux-androideabi"
            elif "arm64" == compiler_info.arch:
              abi_arch = "arm64-v8a"
              toolchain_arch = "aarch64-linux-android"
            else:
              LogError("Unsupported Android architecture.\n")
            additional_options += " -DANDROID_STL=c++_static"
            additional_options += " -DANDROID_ABI=\"%s\"" % abi_arch
            additional_options += " -DANDROID_TOOLCHAIN_NAME=%s-clang" % toolchain_arch

          if first:
            first = False
            for generate in solution.GetGenerates():
              gen_dir = os.path.abspath("%s/gen_%s/%s" % (build_path,  compile_info, generate[0]))
              EnsureDirectory(gen_dir, need_clear)
              os.chdir(gen_dir)
              gen_cmd = BatchCommand("Generate %s" % generate[0], self.env_cfgs)
              gen_cmd.AddCommand("\"%s\" -G \"%s\" %s %s \"%s\"" % (self.cmake_path, compiler_info.generator, additional_options, generate[2], generate[1]))
              gen_cmd.ExecuteEx(0, "gen_%s" % generate[0], "Logs")

          build_dir = os.path.abspath("%s/%s-%s" % (build_path, compile_info, config.lower()))
          EnsureDirectory(build_dir, need_clear)
          EnsureDirectory(binary_path, need_clear, False)
          os.chdir(build_dir)
          cmake_cmd = BatchCommand("CMake %s %s" % (solution.GetName(), config), self.env_cfgs)
          cmake_cmd.AddCommand("\"%s\" -G \"%s\" %s ../cmake" % (self.cmake_path, compiler_info.generator, additional_options))
          cmake_cmd.ExecuteEx(0, "cmake_%s_%s" % (solution.GetName().lower(), config.lower()), "Logs")

          if need_build:
            build_cmd = BatchCommand("Build %s %s" % (solution.GetName(), config), self.env_cfgs)
            if self.compiler_name == "vc":
              build_cmd.AddCommand('@CALL "%s%s" %s' % (compiler_info.compiler_root, compiler_info.vcvarsall_path, vc_option))
              build_cmd.AddCommand('@CD /d "%s"' % build_dir)
            self.MakeAddBuildCommand(build_cmd, make_name, "ALL_BUILD")
            build_cmd.ExecuteEx(0, "build_%s_%s" % (solution.GetName().lower(), config.lower()), "Logs")

          if need_install:
            install_cmd = BatchCommand("Install %s %s" % (solution.GetName(), config), self.env_cfgs)
            if self.compiler_name == "vc":
              install_cmd.AddCommand('@CALL "%s%s" %s' % (compiler_info.compiler_root, compiler_info.vcvarsall_path, vc_option))
              install_cmd.AddCommand('@CD /d "%s"' % build_dir)
            self.MakeAddBuildCommand(install_cmd, make_name, "install")
            install_cmd.ExecuteEx(0, "install_%s_%s" % (solution.GetName().lower(), config.lower()), "Logs")

          os.chdir(curdir)
          sys.stdout.flush()
