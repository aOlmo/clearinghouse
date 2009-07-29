/*
 * This creates a MyISAM table. MyISAM doesn't support transactions. We don't
 * need transactions because we have make very simple single-query database
 * writes.
 */
CREATE TABLE `keys` (
  `id` int(10) unsigned NOT NULL auto_increment,
  /* `pubkeyhash` is never read by our code. We only use it to ensure unique
   * public keys, and the `pubkey` field is too long to specify as unique
   * in mysql. */
  `pubkeyhash` varchar(32) NOT NULL,
  `pubkey` varchar(2048) NOT NULL,
  `privkey` varchar(4096) NOT NULL,
  `description` varchar(255) NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY (`pubkeyhash`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;
