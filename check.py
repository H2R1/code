#!/usr/bin/python2.7
""" Library to assist with developing monitoring checks """

import os, sys, time

verbFlag=False

#################################################################################
def Verbose(msg):
    """ write the msg to stderr if the verbFlag is True """
    if verbFlag:
        sys.stderr.write("%s\n" % msg)

#################################################################################
def exitOk(msg):
    """ print the msg to stdout then exit 0 (OK) """
    print msg
    sys.exit(0)

################################################################################
def exitWarning(msg):
    """ print the msg to stdout then exit 1 (Warning) """
    print msg
    sys.exit(1)

################################################################################
def exitError(msg):
    """ print the msg to stdout then exit 2 (Error) """
    print msg
    sys.exit(2)

################################################################################
def exitUnknown(msg):
    """ print the msg to stdout then exit 3 (Unknown) """
    print msg
    sys.exit(3)

################################################################################
def pingHost(host):
    """ Return True if it can ping the host, or False if it cannot  """
    opsys=os.uname()[0]
    pingcmd={
        'SunOS': '/usr/sbin/ping',
        'Linux': '/bin/ping -c2',
        'AIX': '/etc/ping -c2',
        }
    if opsys in pingcmd:
        f=os.popen("%s %s 2>&1 > /dev/null" % (pingcmd[opsys], host))
        output=f.readline().strip()
        x=f.close()
        if x:
            return False
        else:
            return True
    else:
        check.exitUnknown("pingHost: Unhandled operating system: %s" % opsys)   # pragma: no cover

################################################################################
def maximumProc(processname, maxproc):
    """ Check to make sure that number of processes matching processname is less than
    the Maximum allowed to be running, stored as maxprox. This will alert if the number
    of processes running is greater than maxprox.
    """
    return _proc(processname, maxproc=maxproc)

################################################################################
def minimumProc(processname, minproc):
    """ Check to make sure that the minimum number of processes matching processname
    are running on the host. This will alert if the number of process is less than the
    minproc value.
    """
    return _proc(processname, minproc=minproc)

################################################################################
def oneProc(processname):
    """ Check to make sure that there is only one process matching processname running on this
    host. This will alert if there are either zero ore more than one matching process.
    """
    return _proc(processname, minproc=1, maxproc=1)

################################################################################
def _handleInterpreters(line, opts):
    """ If the process is an interpreter use the script that it is running
    as the command - put it in the output dictionary as 'cmd'
    """
    interpreters=('python','perl','sh', 'ksh', 'zsh')
    ans={}
    bits=line.strip().split(None, len(opts)-1)
    for o in enumerate(opts):
        try:
            ans[o[1]]=bits[o[0]]
        except IndexError:
            # For some reason on older slower boxes the output can get munged
            return {}
    if ans['args'][0]=='[' and ans['args'][-1]==']':  # Linux kernel procs
        ans['cmd']=ans['comm'].split('/')[0]
    else:
        ans['cmd']=os.path.basename(ans['comm'])

    try:
        if os.path.basename(ans['args'].split()[0]) in interpreters:
            idx=1
            ans['cmd']=os.path.basename(ans['args'].split()[idx])
            while ans['cmd'][0]=='-':    # Handle perl -v foo.pl
                ans['cmd']=os.path.basename(ans['args'].split()[idx])
                idx+=1
    except IndexError:
        pass
    return ans

################################################################################
def _proc(processname, minproc=None, maxproc=None):
    """ Check to see that the processname process exists
    There should be minproc < procs < maxproc number of processes
    Return a list of the process ids.
    """
    foundProc=False
    pidlist=[]

    osname=os.uname()[0]
    osver=os.uname()[2]
    if osname=='SunOS':
        if osver == "5.10":
            hostname=os.uname()[1]
            f=os.popen('/bin/ps -eo zone,comm,pid,args')
            for line in f:
                bits=_handleInterpreters(line, ['zone', 'comm','pid', 'args'])
                if bits['zone'] not in ('global',hostname):
                    continue
                if os.path.basename(bits['cmd'])==processname:
                    pidlist.append(bits['pid'])
                    foundProc=True
            f.close()
        else:
            f=os.popen('/bin/ps -eo comm,pid,args')
            for line in f:
                bits=_handleInterpreters(line, ['comm','pid', 'args'])
                if not bits:    # Special case seems to be only Solaris 5.8
                    return []
                if os.path.basename(bits['cmd'])==processname:
                    pidlist.append(bits['pid'])
                    foundProc=True
    elif osname in ('AIX', 'Linux'):
        f=os.popen('/bin/ps -eo comm,pid,args')
        for line in f:
            bits=_handleInterpreters(line, ['comm','pid', 'args'])
            if os.path.basename(bits['cmd'])==processname:
                pidlist.append(bits['pid'])
                foundProc=True
        f.close()
    else:   # pragma: no cover
        exitError("_proc: Unhandled OS: %s" % osname)
    if not foundProc:
        exitError("No %s process found" % processname)
    if minproc and len(pidlist)<minproc:
        exitError("Found not enough (%d<%d) %s processes" % (len(pidlist), minproc, processname))
    if maxproc and len(pidlist)>maxproc:
        exitError("Found too many (%d>%d) %s processes" % (len(pidlist), maxproc, processname))
    return pidlist
    
################################################################################
def timeconv(str):
    """ 
    Convert something vaguely in the format [dd-]hh:mm:ss into
    something usable - ie pure seconds.
    """
    if str=="-":
        return -1
    s=0
    try:
        t=str.split("-")
        if len(t)>1:
            s=s+86400*int(t[0])
            str=t[1]
        else:
            str=t[0]
        t=str.split(":")
        s+=int(t[-1])
        s+=60*int(t[-2])
        if len(t)==3:
            s=s+3600*int(t[0])
    except ValueError:
        sys.stderr.write("Couldn't convert %s to seconds\n" % str)
        return -1
    except IndexError:
        sys.stderr.write("Couldn't convert %s to seconds\n" % str)
    return s

################################################################################
def processList():
    """ Return a list of dictionaries with details about processes that run on the server
    """
    osname=os.uname()[0]
    osver=os.uname()[2]
    ans=[]
    if osname=='Linux':
        f=os.popen('/bin/ps -eo "comm,pid,ppid,user,stime,s,time,etime,args"')
        for line in f:
            if line.startswith('COMMAND'):
                continue
            bits=_handleInterpreters(line, ['comm', 'pid', 'ppid', 'user', 'stime', 's', 'time', 'etime', 'args'])
            bits['etimesecs']=timeconv(bits['etime'])
            ans.append(bits)
        f.close()
    elif osname=='SunOS':
        if osver == "5.10":
            hostname=os.uname()[1]
            f=os.popen('/bin/ps -eo zone,comm,pid,ppid,user,stime,s,time,etime,args')
            for line in f:
                if line.strip().startswith('COMMAND') or line.strip().startswith('ZONE'):
                    continue
                bits=_handleInterpreters(line, ['zone', 'comm', 'pid', 'ppid', 'user', 'stime', 's', 'time', 'etime', 'args'])
                bits['etimesecs']=timeconv(bits['etime'])
                if bits['zone'] not in ('global',hostname):
                    continue
                ans.append(bits)
            f.close()
        else:
            f=os.popen('/bin/ps -eo comm,pid,ppid,user,stime,s,time,etime,args')
            for line in f:
                if line.startswith('COMMAND'):
                    continue
                bits=_handleInterpreters(line, [ 'comm', 'pid', 'ppid', 'user', 'stime', 's', 'time', 'etime', 'args'])
                if bits:
                    bits['etimesecs']=timeconv(bits['etime'])
                    ans.append(bits)
            f.close()
    elif osname=='AIX':
	f=os.popen('/bin/ps -eo comm,pid,ppid,user,time,etime,args')
        for line in f:
            if line.startswith('COMMAND'):
                continue
            bits=_handleInterpreters(line, [ 'comm', 'pid', 'ppid', 'user', 'time', 'etime', 'args'])
            try:
                bits['etimesecs']=timeconv(bits['etime'])
            except KeyError:
                # Defunct processes lose columns under AIX 
                continue
            ans.append(bits)
        f.close()
    else:   # pragma: no cover
        exitUnknown("processList: Unhandled OS: %s" % osname)
    return ans

################################################################################
def fileExists(fname):
    """ Check to make sure that the specified file exists. 
    """
    if not os.path.exists(fname):
        exitError("File %s doesn't exist" % fname)

################################################################################
def portUdpListen(port):
    """  Check that something is listening on the specified UDP port
    """
    Verbose("Checking listening on port %d/udp" % port)
    osname=os.uname()[0]
    if osname=='Linux':
        cmd='/bin/netstat -anu'
    elif osname=='SunOS':
        cmd='/bin/netstat -an -P udp -f inet'
    elif osname=='AIX':
        cmd='/usr/bin/netstat -an -f inet'
    else:   # pragma: no cover
        exitUnknown("portUdpListen - unknown osname %s" % osname)
    foundPort=False
    f=os.popen(cmd)
    for line in f:
        line=line.strip()
        if not line:
            continue
        if osname in ('AIX'):
            if not line.startswith('udp'):
                continue
            localip=line.split()[3]
            if localip=='*.%s' % port:
                foundPort=True
            else:
                localport=localip.split('.')[-1]
                if str(localport)==str(port):
                    foundPort=True
        if osname=='SunOS':
            if line.split()[-1]=='Idle':
                localaddr=line.split()[0]
                if localaddr=='*.%s' % port:
                    foundPort=True
                else:
                    localport=localaddr.split('.')[-1]
                    if str(localport)==str(port):
                        foundPort=True
        if osname=='Linux':
            if not line.startswith('udp'):
                continue
            localaddr=line.split()[3]
            if localaddr=='0.0.0.0:%s' % port:
                foundPort=True
            else:
                localport=localaddr.split(':')[-1]
                if str(localport)==str(port):
                    foundPort=True
    f.close()
    if not foundPort:
        exitError("Nothing listening on port %s/udp" % port)

################################################################################
def portTcpListen(port, ip=None):
    """  Check that something is listening on the specified TCP port
    """
    if type(port)!=type(1):
        try:
            port=int(port)
        except ValueError:
            exitUnknown("Port must be a number not %s" % port)
    Verbose("Checking listening on port %d/tcp" % port)
    osname=os.uname()[0]
    if osname=='Linux':
        cmd='/bin/netstat -ant'
    elif osname=='SunOS':
        cmd='/bin/netstat -an -P tcp -f inet'
    elif osname=='AIX':
        cmd='/usr/bin/netstat -an -f inet'
    else:   # pragma: no cover
        exitUnknown("portTcpListen - unknown osname %s" % osname)
    foundPort=False
    f=os.popen(cmd)
    for line in f:
        if 'LISTEN' not in line:
            continue
        # Check for unbound port
        if '*.%s ' % port in line:
            foundPort=True
            return '0.0.0.0', port
        elif '0.0.0.0:%s ' % port in line:
            foundPort=True
            return '0.0.0.0', port
        elif ':::%s ' % port in line:
            foundPort=True
            return '0.0.0.0', port
        else:
            # Check for ports bound to an IP
            if osname=='SunOS':
                localaddr = line.split()[0]
                localport = localaddr.split('.')[-1]
                localip   = ".".join(localaddr.split('.')[0:4])
                if ip and ip != localip:
                    continue
                if str(localport)==str(port):
                    foundPort=True
                    return localip, localport

            elif osname=='Linux':
                localaddr = line.split()[3]
                localport = localaddr.split(':')[-1]
                localip   = localaddr.split(':')[0]
                if ip and ip != localip:
                    continue
                if str(localport)==str(port):
                    foundPort=True
                    return localip, localport

            elif osname=='AIX':
                localaddr = line.split()[3]
                localport = localaddr.split('.')[-1]
                localip   = ".".join(localaddr.split('.')[0:4])
                if ip and ip != localip:
                    continue
                if str(localport)==str(port):
                    foundPort=True
                    return localip, localport
    f.close()
    if ip and not foundPort:
        exitError("Nothing listening on %s:%s/tcp" % (ip, port))

    if not foundPort:
        exitError("Nothing listening on port %s/tcp" % port)

################################################################################
def portListen(port):
    """  Check that something is listening on the specified port
        By default we check TCP
    """
    return portTcpListen(port)

################################################################################
def processListen(pid):
    """ Check to make sure that the process pid is listening
    """
    Verbose("Checking Listening of process %s" % pid)
    pathlist=('/usr/local/bin/lsof', '/usr/sbin/lsof')
    foundListen=False
    foundLsof=False
    for path in pathlist:
        if os.path.exists(path):
            foundLsof=True
            f=os.popen('%s -p %s' % (path, pid))
            for line in f:
                if 'LISTEN' in line:
                    foundListen=True
            f.close()
    if foundLsof and not foundListen:
        exitError("process %d not listening to anyone" % pid)

############################################################################
def oldestFile(dir, ext=None, ignore_dir=False):
    """ Return the age of the oldest file in the specified dir
        with the specified extension
    """
    files=os.listdir(dir)
    oldest=time.time()
    for f in files:
        # if the ignore_dir flag is true, then skip over all directories
        if ignore_dir and os.path.isdir('%(dir)s/%(f)s' % locals() ):
            continue     
        if not ext or f.endswith(ext):
            mtime=os.stat(os.path.join(dir,f)).st_mtime
            oldest=min(mtime,oldest)
    return oldest

############################################################################
def numberOfFiles(direct, ext=None, minfile=None, maxfile=None):
    """ Return the number of files in the specified directory
    """
    num=len([f for f in os.listdir(direct) if not ext or f.endswith(ext)])
    if not ext:
        ext=""
    if minfile and num<minfile:
        exitError("Found not enough files (%d<%d) %s files in %s" % (num, minfile, ext, direct))
    if maxfile and num>maxfile:
        exitError("Found too many files (%d>%d) %s files in %s" % (num, maxfile, ext, direct))
    return num

############################################################################
def _ftp_callback(*args, **kwargs):
    """ Callback used by ftpCheck to stop it spewing stuff to stdout
    """
    pass

############################################################################
def ftpCheck(host=None, user=None, password=None, destdir=None):
    """ Check to make sure that FTP is working
    And measure how it works while we are there
    """
    import ftplib

    try:
        start_time = time.time()
        ftp = ftplib.FTP(host)
        connect_time = time.time()
        ftp.login(user,password)
        login_time = time.time()
        if destdir:
            ftp.cwd(destdir)
        ftp.retrlines('LIST', _ftp_callback)
        lst_time = time.time()
        ftp.close()
        close_time = time.time()
    except ftplib.all_errors, err:
        exitError("Failed on FTP to %s: %s" % (host, err.message))
        

############################################################################
def snmpGet(oid, host='localhost', community='public'):
    """ use SNMP to get SNMP data from host """
    from pysnmp.entity.rfc3413.oneliner import cmdgen
    authdata=cmdgen.CommunityData('libtool', community)
    transport=cmdgen.UdpTransportTarget((host, 161))
    errIndication, errStatus, errorIndex, varBinds=cmdgen.CommandGenerator().getCmd(authdata, transport, oid)
    if errIndication:
        # Need to put some better error handling in
        return None

    return varBinds[0][1].prettyPrinter()

############################################################################
def snmpWalk(oid, host='localhost', community='public'):
    """ use SNMP to walk SNMP data from host """
    from pysnmp.entity.rfc3413.oneliner import cmdgen
    authdata=cmdgen.CommunityData('libtool', community)
    transport=cmdgen.UdpTransportTarget((host, 161))

    errIndication, errStatus, errorIndex, varBindTable=cmdgen.CommandGenerator().nextCmd(authdata, transport, oid)

    if errIndication:
        # Need to put some better error handling in
        return {}

    ans={}
    for varrow in varBindTable:
        ans[varrow[0][0]]=varrow[0][1]
    return ans

################################################################################
def snmpTable(oidmap, host):
    """
    oidmap is a list of tuples and looks like:
        oidmap=[
            ('connUnitPortState', (1,3,6,1,3,94,1,10,1,6), stateMap),
            ('connUnitPortStatus', (1,3,6,1,3,94,1,10,1,7), {}),
            ('connUnitPortBunny', (1,3,6,1,3,94,1,10,1,8), convFn),
            ]
        The tuple is:
            Part 1) Label - generally the OID name
            Part 2) (OID)
            Part 3) Mapper
                Either a dictionary which maps the key to the value
                    stateMap={1: 'unknown', 2:'online', 3:'offline', 4:'bypassed', 5:'diagnostics' }
                Or an executable which returns the appropriate value e.g. def fn(x) return y
    """
    from pysnmp.entity.rfc3413.oneliner import cmdgen
    table={}
    tmp={}

    # Walk for each oid
    for lbl, oid, mp in oidmap:
        tmp[lbl]=snmpWalk(oid, host)

    for lbl,oid,mp in oidmap:
        for i in tmp[lbl].keys():
            tblindex=i[-1]
            if tblindex not in table:
                table[tblindex]={}
            if callable(mp):
                table[tblindex][lbl]=mp(tmp[lbl][i])
            else:
                if tmp[lbl][i] in mp:
                    table[tblindex][lbl]=mp[tmp[lbl][i]]
                else:
                    table[tblindex][lbl]=tmp[lbl][i]

    return table

################################################################################
def packageInfo(pkgname):
    """ Return the version of the package installed or empty string if the package
    is not installed

    Note that this is potentially insecure as it doesn't bless commands
    """
    vers=''
    if ';' in pkgname or '`' in pkgname:
        exitError("Problem with check.packageInfo")
    if not pkgname.strip():
        exitError("Problem with check.packageInfo")
    if os.uname()[0]=='SunOS':
        f=os.popen('/bin/pkginfo -l %s 2>/dev/null' % pkgname)
        for line in f:
            if 'VERSION' in line:
                vers=line.split(':')[-1].strip()
        f.close()
    elif os.uname()[0]=='Linux':
        f=os.popen('rpm -q %s 2>/dev/null' % pkgname)
        for line in f:
            if line.startswith(pkgname):
                vers=line.replace("%s-" % pkgname, '').strip()
        f.close()
    return vers
    
################################################################################
def lineSkipper(line, start=[], middle=[], end=[]):
    """ Convenience function to assist with file parseing
    If any of the strings in start occur at the start of the line then return True
    Similar for middle and end for the middle and end of the line
    Return False if none of them match
    """
    if not line:
        return True
    for sstring in start:
        if line.startswith(sstring):
            return True
    for estring in end:
        if line.endswith(estring):
            return True
    for mstring in middle:
        if mstring in line:
            return True
    return False
        
#EOF
