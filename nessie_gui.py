#!/usr/bin/python -i

# The MIT License
#
# Copyright (c) 2007 Damon Kohler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Nessie"s GUI."""

__author__ = 'damonkohler@gmail.com (Damon Kohler)'

import logging
import nessie
import nessie_console
import socket
import wx
import wx.lib.newevent

# Custom Nessie events.
PrintMessageEvent, EVT_PRINT_MESSAGE = wx.lib.newevent.NewEvent()


class GridBagSizerFactory(object):

  def __init__(self, hgap, vgap):
    self.sizer = wx.GridBagSizer(hgap, vgap)
    self._row = 0
    self._col = 0

  def _Add(self, obj, *args, **kwargs):
    self.sizer.Add(obj, (self._row, self._col), *args, **kwargs)

  def Add(self, *args, **kwargs):
    self._Add(*args, **kwargs)
    self.NewCol()

  def AddGrowable(self, *args, **kwargs):
    self._Add(*args, **kwargs)
    self.sizer.AddGrowableCol(self._col)
    self.NewCol()

  def NewCol(self):
    self._col += 1

  def NewRow(self):
    self._col = 0
    self._row += 1

  def NewGrowableRow(self):
    self.NewRow()
    self.sizer.AddGrowableRow(self._row)


class ConfigurationDialog(wx.Dialog):

  def __init__(self, *args, **kwargs):
    wx.Dialog.__init__(self, *args, **kwargs)
    self.nick_txt = wx.TextCtrl(self)
    self.host_txt = wx.TextCtrl(self)
    self.host_txt.Value = nessie.GetPublicIpAddress()
    self.port_txt = wx.TextCtrl(self)
    self.network_key_txt = wx.TextCtrl(self)
    save_btn = wx.Button(self, -1, 'Save')
    save_btn.Bind(wx.EVT_BUTTON, self.SaveConfiguration)
    sizer_factory = GridBagSizerFactory(5, 5)
    sizer_factory.Add(wx.StaticText(self, label='Nickname'), (1, 1))
    sizer_factory.AddGrowable(self.nick_txt, (1, 1), wx.EXPAND)
    sizer_factory.NewRow()
    sizer_factory.Add(wx.StaticText(self, label='Host address'), (1, 1))
    sizer_factory.AddGrowable(self.host_txt, (1, 1), wx.EXPAND)
    sizer_factory.NewRow()
    sizer_factory.Add(wx.StaticText(self, label='Host port'), (1, 1))
    sizer_factory.AddGrowable(self.port_txt, (1, 1), wx.EXPAND)
    sizer_factory.NewRow()
    sizer_factory.Add(wx.StaticText(self, label='Network key'), (1, 1))
    sizer_factory.AddGrowable(self.network_key_txt, (1, 1), wx.EXPAND)
    sizer_factory.NewRow()
    sizer_factory.Add(save_btn, (1, 1))
    self.SetSizerAndFit(sizer_factory.sizer)
    self.SetSizeWH(200, -1)

  def SaveConfiguration(self, event=None):
    self.Hide()


class MainWindow(wx.Frame):

  def __init__(self, *args, **kwargs):
    wx.Frame.__init__(self, *args, **kwargs)
    self.me = None
    # Add UI components and handlers.
    config_btn = wx.Button(self, label='Config')
    config_btn.Bind(wx.EVT_BUTTON, self.ShowConfiguration)
    add_node_btn = wx.Button(self, label='Add Node')
    add_node_btn.Bind(wx.EVT_BUTTON, self.AddNode)
    self.chat_log_txt = wx.TextCtrl(self, style=wx.TE_MULTILINE)
    self.chat_log_txt.Bind(EVT_PRINT_MESSAGE, self.PrintMessage)
    self.nodes_lbx = wx.ListBox(self)
    self.chat_txt = wx.TextCtrl(self)
    self.chat_txt.Bind(wx.EVT_KEY_DOWN, self.Chat)
    # Create sizer to arrange components.
    sizer_factory = GridBagSizerFactory(5, 5)
    sizer_factory.Add(config_btn, (1, 1))
    sizer_factory.Add(add_node_btn, (1, 1))
    sizer_factory.NewGrowableRow()
    sizer_factory.AddGrowable(self.chat_log_txt, (1, 1), wx.EXPAND)
    sizer_factory.Add(self.nodes_lbx, (1, 1), wx.EXPAND)
    sizer_factory.NewRow()
    sizer_factory.Add(self.chat_txt, (1, 2), wx.EXPAND)
    self.SetSizer(sizer_factory.sizer)
    # Create configuration dialog.
    self.config_dlg = ConfigurationDialog(self, title='Configuration')
    self.CreateStatusBar()
    self.Center()
    self.Show()

  def AddNode(self, event=None):
    dlg = wx.TextEntryDialog(self, 'Enter nickname for node.', 'Add Node')
    if dlg.ShowModal() == wx.ID_OK:
      nick = str(dlg.GetValue())
      self.SetStatusText('Adding node %s. Please wait.' % nick)
      try:
        self.me.AddPeer(nick)
      except nessie.NessieError:
        self.SetStatusText('Failed to add node %s.' % nick)
      else:
        self.SetStatusText('Added node %s.' % nick)
        self.nodes_lbx.Set(self.me.GetPeerNicknames())
    dlg.Destroy()

  def ShowConfiguration(self, event=None):
    self.config_dlg.Center()
    self.config_dlg.ShowModal()
    nick = str(self.config_dlg.nick_txt.Value)
    network_key = str(self.config_dlg.network_key_txt.Value)
    host = str(self.config_dlg.host_txt.Value)
    port = int(self.config_dlg.port_txt.Value)
    self.me = GuiNessie(self.chat_log_txt, nick, network_key, host, port)
    self.me.Serve()

  def Chat(self, event=None):
    if event.GetRawKeyCode() == 9229:  # Pressed enter key.
      msg = str(self.chat_txt.Value)
      self.me.Chat(msg)
      self.chat_log_txt.Value += 'me> %s\n' % msg
      self.chat_txt.Value = ''
    else:
      event.Skip()

  def PrintMessage(self, event=None):
    self.chat_log_txt.Value += '%s\n' % event.msg


class GuiNessie(nessie_console.NessieConsole):

  def __init__(self, chat_log_txt, *args, **kwargs):
    nessie_console.NessieConsole.__init__(self, *args, **kwargs)
    self.chat_log_txt = chat_log_txt

  def export_PrintMessage(self, peer_id, msg):
    msg = self._Decrypt(msg)
    msg = '%s> %s' % (peer_id, msg)
    print 'here %r' % msg
    wx.PostEvent(self.chat_log_txt, PrintMessageEvent(msg=msg))
    return 0


if __name__ == '__main__':
  app = wx.App(redirect=False)
  frame = MainWindow(None, title='Nessie', size=wx.Size(520, 480))
  app.MainLoop()
