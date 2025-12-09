-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Vært: mariadb
-- Genereringstid: 09. 12 2025 kl. 17:15:48
-- Serverversion: 10.6.20-MariaDB-ubu2004
-- PHP-version: 8.3.26

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `x`
--

-- --------------------------------------------------------

--
-- Struktur-dump for tabellen `comments`
--

CREATE TABLE `comments` (
  `comment_pk` varchar(36) NOT NULL,
  `comment_user_fk` varchar(36) NOT NULL,
  `comment_post_fk` varchar(36) NOT NULL,
  `comment_message` text NOT NULL,
  `comment_created_at` int(10) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Data dump for tabellen `comments`
--

INSERT INTO `comments` (`comment_pk`, `comment_user_fk`, `comment_post_fk`, `comment_message`, `comment_created_at`) VALUES
('237fe75fe3f04a65abfc6396afa08f2d', '92d1eb84b1124ba8a5ee348f957de1d3', '28dd4c1671634d73acd29a0ab109bef1', 'love the posts', 1764870986),
('42c84c6863184e3a8392ae13bd7f9f8c', '262f7fd26d234ebca93d297e4f1036d2', '3f534678ba324c3aa2624c1f118573f7', 'hello', 1763667969),
('6aea7d7531994de3912e7716081c771d', '262f7fd26d234ebca93d297e4f1036d2', '28dd4c1671634d73acd29a0ab109bef1', 'voila!', 1763667726),
('9182147aa83945eb99f6695da8475d91', '92d1eb84b1124ba8a5ee348f957de1d3', '35bbd3907a6e4517bd77e89f4f69ac20', 'glad for det virker', 1764870977),
('dc6c07ecd96447e18c0fe928441df84c', '262f7fd26d234ebca93d297e4f1036d2', 'f80d90cbf7174cbe8a06694a7d11798f', 'it is really lovely', 1764700090),
('ee273c121b024680b4fe7b9437fc9927', '262f7fd26d234ebca93d297e4f1036d2', '28dd4c1671634d73acd29a0ab109bef1', 'voila!', 1763667726);

--
-- Triggers/udløsere `comments`
--
DELIMITER $$
CREATE TRIGGER `decrement_post_comments` AFTER DELETE ON `comments` FOR EACH ROW UPDATE posts 
    SET post_comments = post_comments - 1
    WHERE post_pk = OLD.comment_post_fk
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `increment_post_comments` AFTER INSERT ON `comments` FOR EACH ROW UPDATE posts 
    SET post_comments = post_comments + 1
    WHERE post_pk = NEW.comment_post_fk
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Struktur-dump for tabellen `follows`
--

CREATE TABLE `follows` (
  `follow_pk` varchar(36) NOT NULL,
  `follow_follower_fk` varchar(36) NOT NULL,
  `follow_following_fk` varchar(36) NOT NULL,
  `follow_created_at` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Data dump for tabellen `follows`
--

INSERT INTO `follows` (`follow_pk`, `follow_follower_fk`, `follow_following_fk`, `follow_created_at`) VALUES
('3d8c93b9019c411b986ec38b04f7700e', '262f7fd26d234ebca93d297e4f1036d2', '21e66977ccb74fdbb6cbdb3e7e3a12cb', 1764763186),
('5148b9540b9543e987a9be879f39a96f', '262f7fd26d234ebca93d297e4f1036d2', '59ac8f8892bc45528a631d4415151f13', 1764702525),
('6f9b0ad361cb4d56a99666b432be85d5', '262f7fd26d234ebca93d297e4f1036d2', '92d1eb84b1124ba8a5ee348f957de1d3', 1764871398),
('885fc4e7057a425299b61ff05cd58d74', '262f7fd26d234ebca93d297e4f1036d2', '6b48c6095913402eb4841529830e5415', 1764702993),
('9b3a5a1b295e4cc2ab27f869e2ca0143', '262f7fd26d234ebca93d297e4f1036d2', '805a39cd8c854ee8a83555a308645bf5', 1764763284),
('ed0efb84dbbc4cedb4e244704f4918dc', '92d1eb84b1124ba8a5ee348f957de1d3', '262f7fd26d234ebca93d297e4f1036d2', 1764872527);

--
-- Triggers/udløsere `follows`
--
DELIMITER $$
CREATE TRIGGER `decrement_followers` AFTER DELETE ON `follows` FOR EACH ROW BEGIN
    -- Opdater antal followers for den der bliver unfollowed
    UPDATE users 
    SET user_followers = user_followers - 1
    WHERE user_pk = OLD.follow_following_fk;
    
    -- Opdater antal following for den der unfollower
    UPDATE users 
    SET user_following = user_following - 1
    WHERE user_pk = OLD.follow_follower_fk;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `increment_followers` AFTER INSERT ON `follows` FOR EACH ROW BEGIN
    -- Opdater antal followers for den der bliver fulgt
    UPDATE users 
    SET user_followers = user_followers + 1
    WHERE user_pk = NEW.follow_following_fk;
    
    -- Opdater antal following for den der følger
    UPDATE users 
    SET user_following = user_following + 1
    WHERE user_pk = NEW.follow_follower_fk;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Struktur-dump for tabellen `likes`
--

CREATE TABLE `likes` (
  `like_pk` varchar(36) NOT NULL,
  `like_user_fk` varchar(36) NOT NULL,
  `like_post_fk` varchar(36) NOT NULL,
  `like_created_at` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Data dump for tabellen `likes`
--

INSERT INTO `likes` (`like_pk`, `like_user_fk`, `like_post_fk`, `like_created_at`) VALUES
('17dc31ee787144adac918f91f74d8b16', '92d1eb84b1124ba8a5ee348f957de1d3', '18f9475a49da4958876cdd8cecd26ffe', 1764870990),
('183eeb63cd2443e39799d7c17a1dc74f', '262f7fd26d234ebca93d297e4f1036d2', 'b8f59662ce5b4b58bf19a5fe0eda3122', 1763665747),
('2e8229cf07a14470a398ee06e8772346', '262f7fd26d234ebca93d297e4f1036d2', 'efaf8b6f98be4a7b8cc7a75d0f83578c', 1763665794),
('48dce7312e7b4e4e91f324d592805638', '92d1eb84b1124ba8a5ee348f957de1d3', '28dd4c1671634d73acd29a0ab109bef1', 1764678408),
('68eebb212fa64becb27c68c2961ae066', '262f7fd26d234ebca93d297e4f1036d2', 'dc4a4363c6dd4e31ab8497973ea8af3b', 1763665589),
('7c85e68876aa469dabeaf099edf06596', '262f7fd26d234ebca93d297e4f1036d2', '3f534678ba324c3aa2624c1f118573f7', 1764714184),
('a9d1b4de0c9e47aa965b91dd27e527e7', '262f7fd26d234ebca93d297e4f1036d2', '28dd4c1671634d73acd29a0ab109bef1', 1763667658),
('b34ef072fb3d495397c15b684363eb6a', '262f7fd26d234ebca93d297e4f1036d2', '0cf34e2cfa8045698dc102b082cab826', 1764947863),
('b76a7186b0b548998769bd95c0d334fe', '262f7fd26d234ebca93d297e4f1036d2', 'f9c1bcf6c7f244b88bff7a216702ca16', 1765296280),
('f3d8f94002864e6886df92943409b48e', '262f7fd26d234ebca93d297e4f1036d2', 'f80d90cbf7174cbe8a06694a7d11798f', 1764700083);

--
-- Triggers/udløsere `likes`
--
DELIMITER $$
CREATE TRIGGER `decrement_post_total_likes` AFTER DELETE ON `likes` FOR EACH ROW UPDATE posts 
    SET post_total_likes = post_total_likes - 1
    WHERE post_pk = OLD.like_post_fk
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `post_total_likes` AFTER INSERT ON `likes` FOR EACH ROW UPDATE posts 
    SET post_total_likes = post_total_likes + 1
    WHERE post_pk = NEW.like_post_fk
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Struktur-dump for tabellen `posts`
--

CREATE TABLE `posts` (
  `post_pk` char(32) NOT NULL,
  `post_user_fk` char(32) NOT NULL,
  `post_message` varchar(280) NOT NULL,
  `post_total_likes` bigint(20) UNSIGNED NOT NULL,
  `post_comments` int(10) UNSIGNED DEFAULT 0,
  `post_updated_at` bigint(20) DEFAULT NULL,
  `post_created_at` bigint(20) UNSIGNED NOT NULL,
  `post_is_blocked` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Data dump for tabellen `posts`
--

INSERT INTO `posts` (`post_pk`, `post_user_fk`, `post_message`, `post_total_likes`, `post_comments`, `post_updated_at`, `post_created_at`, `post_is_blocked`) VALUES
('0cf34e2cfa8045698dc102b082cab826', '262f7fd26d234ebca93d297e4f1036d2', 'kan jeg lave post nu, Bla bla bla', 1, 0, 1765274684, 1764947854, 0),
('12cd29ecc74341e9a4f14ed2df25374b', '262f7fd26d234ebca93d297e4f1036d2', 'kan jeg lave post nu', 0, 0, NULL, 1764947748, 0),
('18f9475a49da4958876cdd8cecd26ffe', '262f7fd26d234ebca93d297e4f1036d2', 'i fucking hate witter nr 2', 1, 0, NULL, 1764783197, 0),
('1be3192e46be416694f14e10fe9f3e2b', '92d1eb84b1124ba8a5ee348f957de1d3', 'what is happening', 0, 0, 1764876413, 1764875721, 0),
('1e5ecc804e1f46bc8e723437bf4bfc4b', '225a9fc15b8f409aa5c8ee7eafee516b', 'And this just works!', 0, 0, NULL, 0, 0),
('258aeac7242348058c8c36f025b10fd5', '225a9fc15b8f409aa5c8ee7eafee516b', 'tes5', 0, 0, NULL, 0, 0),
('28dd4c1671634d73acd29a0ab109bef1', '805a39cd8c854ee8a83555a308645bf5', 'My first super life !', 2, 3, NULL, 0, 0),
('299323cf81924589b0de265e715a1f9e', '225a9fc15b8f409aa5c8ee7eafee516b', 'test3', 0, 0, NULL, 0, 0),
('3572cdeea931447ca25f859bf6d0f0fe', '92d1eb84b1124ba8a5ee348f957de1d3', 'Lovely app', 0, 0, NULL, 1764873438, 0),
('35bbd3907a6e4517bd77e89f4f69ac20', '262f7fd26d234ebca93d297e4f1036d2', 'Luksus, det virker faktik nu, så nu kan jeg skrive lange beskeder', 0, 1, 1764775433, 0, 0),
('3cb78d73518c4c01a29ad33d196ce962', '225a9fc15b8f409aa5c8ee7eafee516b', 'This is new', 0, 0, NULL, 0, 0),
('3e4f0c3ab65344d8b79c849400418758', '225a9fc15b8f409aa5c8ee7eafee516b', 'test1', 0, 0, NULL, 0, 0),
('3f534678ba324c3aa2624c1f118573f7', '6b48c6095913402eb4841529830e5415', 'dfdfd', 1, 1, NULL, 0, 0),
('50293af4d1f64798af9b7dfcbf5ed3e7', '225a9fc15b8f409aa5c8ee7eafee516b', 'new', 0, 0, NULL, 0, 0),
('5b147eb4f0064bd9be7f18e6be2b3347', '225a9fc15b8f409aa5c8ee7eafee516b', 'First great test', 0, 0, NULL, 0, 0),
('616c38c6e9e14406a92439e2d81490fc', '225a9fc15b8f409aa5c8ee7eafee516b', 'A browser', 0, 0, NULL, 0, 0),
('63ed90b8cafc47fa9a3253fa1ecfeb04', '225a9fc15b8f409aa5c8ee7eafee516b', 'this', 0, 0, NULL, 0, 0),
('69d3ed14f15047139b6cd8bd8180c104', '59ac8f8892bc45528a631d4415151f13', 'This is Daniel\'s post', 0, 0, NULL, 0, 0),
('6b7bc6fd2b57486db21325030f63fd90', '6b48c6095913402eb4841529830e5415', 'erere', 0, 0, NULL, 0, 0),
('79c5470b54da40f5ac19729738b37a38', '6b48c6095913402eb4841529830e5415', 'dfdfd', 0, 0, NULL, 0, 0),
('7d6f40e626c54efaa32494bce5f739d7', '88a93bb5267e443eb0047f421a7a2f34', 'test', 0, 0, NULL, 0, 0),
('94201aa1d42f4da092d0524f55de5b1c', '92d1eb84b1124ba8a5ee348f957de1d3', 'Virker det nu?', 0, 0, NULL, 1764873713, 0),
('99fefea24ea5419da19ed1f8cf8e9499', '225a9fc15b8f409aa5c8ee7eafee516b', 'wow', 0, 0, NULL, 0, 0),
('ad95e1d3f62f4d07b7bf9e3e6d4dd527', '225a9fc15b8f409aa5c8ee7eafee516b', 'And this just works!', 0, 0, NULL, 0, 0),
('b4b23963a6a4479e918e66f47baef200', '225a9fc15b8f409aa5c8ee7eafee516b', 'test1', 0, 0, NULL, 0, 0),
('bb640996826b4a519a4bd72ceafe2e62', '92d1eb84b1124ba8a5ee348f957de1d3', 'what', 0, 0, NULL, 1764873825, 0),
('bcaa6df8880e411a9c25deaafae2314a', '225a9fc15b8f409aa5c8ee7eafee516b', 'test4', 0, 0, NULL, 0, 0),
('cbc7834baf2f4cd6af344ed62aa6e21f', '92d1eb84b1124ba8a5ee348f957de1d3', 'hvad nu er dr galt?', 0, 0, NULL, 1764875797, 0),
('cc4e19261cf5496f9185d6fb8d2c723d', '92d1eb84b1124ba8a5ee348f957de1d3', 'Hvorfor komemr der en box nedenunder', 0, 0, NULL, 1764873558, 0),
('f80d90cbf7174cbe8a06694a7d11798f', '262f7fd26d234ebca93d297e4f1036d2', 'lovelyLOVLY', 1, 1, 1764774117, 0, 0);

-- --------------------------------------------------------

--
-- Struktur-dump for tabellen `trends`
--

CREATE TABLE `trends` (
  `trend_pk` char(32) NOT NULL,
  `trend_title` varchar(100) NOT NULL,
  `trend_message` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Data dump for tabellen `trends`
--

INSERT INTO `trends` (`trend_pk`, `trend_title`, `trend_message`) VALUES
('6543c995d1af4ebcbd5280a4afaa1e2c', 'Politics are rotten', 'Everyone talks and only a few try to do something'),
('8343c995d1af4ebcbd5280a6afaa1e2d', 'New rocket to the moon', 'A new rocket has been sent towards the moon, but id didn\'t make it');

-- --------------------------------------------------------

--
-- Struktur-dump for tabellen `users`
--

CREATE TABLE `users` (
  `user_pk` char(32) NOT NULL,
  `user_email` varchar(100) NOT NULL,
  `user_password` varchar(255) NOT NULL,
  `user_username` varchar(20) NOT NULL,
  `user_first_name` varchar(20) NOT NULL,
  `user_last_name` varchar(20) NOT NULL DEFAULT '',
  `user_avatar_path` varchar(50) NOT NULL,
  `user_verification_key` char(36) NOT NULL,
  `user_verified_at` bigint(20) UNSIGNED NOT NULL,
  `user_bio` varchar(250) NOT NULL,
  `user_followers` bigint(20) DEFAULT 0,
  `user_following` bigint(20) DEFAULT 0,
  `user_cover_path` varchar(50) NOT NULL,
  `user_admin` tinyint(1) NOT NULL,
  `user_is_blocked` tinyint(1) NOT NULL,
  `user_deleted_at` bigint(20) UNSIGNED DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Data dump for tabellen `users`
--

INSERT INTO `users` (`user_pk`, `user_email`, `user_password`, `user_username`, `user_first_name`, `user_last_name`, `user_avatar_path`, `user_verification_key`, `user_verified_at`, `user_bio`, `user_followers`, `user_following`, `user_cover_path`, `user_admin`, `user_is_blocked`, `user_deleted_at`) VALUES
('21e66977ccb74fdbb6cbdb3e7e3a12cb', 'daniel@gmail.com', 'scrypt:32768:8:1$OSL1Z4fWygxh9s2t$c5404c596d389e4fc1fc36a2853ee5f662ab4903476210424a325c50fa7ac64729716f3156687d789c6d895b9876ef069ced40e0e84a7372ca758ffa3a692960', 'daniel', 'Daniel', '', '', 'c29fa5894f224964953801c925a7cac5', 0, '', 1, 0, '', 0, 0, NULL),
('262f7fd26d234ebca93d297e4f1036d2', 'malenadreyer@gmail.com', 'scrypt:32768:8:1$1Tv7BCtkFiRcaD7u$e918c402a906ecb599f2a9d05134359264181393b771c70beb392065b172f410eb234637082fa495129db354c5d3fdce127d566b170c043b80094da6cccf92ae', 'malenadreyer', 'Maria', 'Dreyer', 'db5b7c513fd64f248f6fd47b253ff121.png', '', 1762978693, 'Maria loves Webdev exam and is not nervous', 1, 5, '446f5e8ce72c43e2a4f140ba0c0494a7.png', 1, 0, NULL),
('59ac8f8892bc45528a631d4415151f13', 'terese@gmail.com', 'scrypt:32768:8:1$Tq056RbRH27Mc9g3$84810a2576e4828498be40c7f51f33e59d19d136e0c5c12e31fb676f3141934c639e088530f9be4ce682cbdfd4eaec34e1220fa7121bf8779e7de0bff29115b9', 'Mily', 'Mille', '', '', '', 45665656, '', 1, 0, '', 0, 0, NULL),
('6b48c6095913402eb4841529830e5415', 'a@a.com', 'scrypt:32768:8:1$rRjuDGIwaA31YlPi$f73f9a059fb3757ba6724d9c94e2a192d8b8d59fcd18d7b11c57e508f1b9cfb94bb7c6fd4f8d632b777e31cd47aef9c95adcad2451786cbb7e7c073fe8cbaf3a', 'Sofi', 'Sofie', '', '', '', 45445, '', 1, 0, '', 0, 0, NULL),
('7f77427481fd4148ae3d874f2e1d72fb', 'michael.lindholm@gmail.com', 'scrypt:32768:8:1$Ew32RTGhHlwqjbYL$f759ad54c3114cb172d5aea012c5b354902b3a0cebb34e019a30d2180e2aeb9a5ba361b206333e25e5b76191b0337b99bda41776dcb1b0b30894b80ebacafb23', 'michael.lindhol', 'Michael', '', '', 'bbc9e21514be4dc69dede10726c38b64', 0, 'Mit navn er Michael, jeg elsker Maria', 0, 0, '', 0, 0, NULL),
('805a39cd8c854ee8a83555a308645bf5', 'fullflaskdemomail@gmail.com', 'scrypt:32768:8:1$VlBgiW1xFsZuKRML$a5f61d62ac3f45d42c58cf8362637e717793b8760f026b1b47b7bfec47037abbe13e1c20e8bdc66fc03cc153d0bcf6185e15cf25ad58eb9d344267882dd7e78c', 'santiago', 'Santiago', '', '', '', 565656, '', 1, 0, '', 0, 0, NULL),
('92d1eb84b1124ba8a5ee348f957de1d3', 'michael.lindholm@outlook.com', 'scrypt:32768:8:1$nB4E2KCGjuRY32Nw$770fb9e53bfee145337ed7b8be1cc9cf1c6f2481f4935d57dde86542037c17320853997f9fee1fde747f4ee10de3318010e41690eb2204ea423df74538fbaf84', 'michael', 'Michael', 'Lindholm', '9bc533d981d04aaa852da9903305448e.png', '', 1762984486, 'My name is Michael and i help Maria with coding!', 1, 1, '090e6602e63c4e29a1ac17a3b96b374e.png', 0, 0, NULL),
('a7b85cdc57e34850b4c21eda559f61a1', 'madr0002@stud.ek.dk', 'scrypt:32768:8:1$ZMdhowh9C25VgWWZ$647fa76fe6cb79ef65baf1895a0e63dd0affba50f10db9c8d66d6bf334908a0a4f845adc2d7db4a4d94748b88f9343bd1024c5dc09123155c68fd0a6df549115', 'ElonTusk', 'Elon', 'Tusk', 'ead16f3f6e8c4b888527149a5ed431dc.png', '', 1765290581, 'My name is Elon Tusk', 0, 0, '37f5a373589241e98aa9b01f7b7dd0e0.png', 0, 0, 1765296667);

--
-- Begrænsninger for dumpede tabeller
--

--
-- Indeks for tabel `comments`
--
ALTER TABLE `comments`
  ADD PRIMARY KEY (`comment_pk`),
  ADD KEY `comment_user_fk` (`comment_user_fk`),
  ADD KEY `comment_post_fk` (`comment_post_fk`);

--
-- Indeks for tabel `follows`
--
ALTER TABLE `follows`
  ADD PRIMARY KEY (`follow_pk`),
  ADD UNIQUE KEY `unique_follow` (`follow_follower_fk`,`follow_following_fk`),
  ADD KEY `follow_following_fk` (`follow_following_fk`);

--
-- Indeks for tabel `likes`
--
ALTER TABLE `likes`
  ADD PRIMARY KEY (`like_pk`),
  ADD UNIQUE KEY `unique_like` (`like_user_fk`,`like_post_fk`),
  ADD KEY `like_post_fk` (`like_post_fk`);

--
-- Indeks for tabel `posts`
--
ALTER TABLE `posts`
  ADD PRIMARY KEY (`post_pk`),
  ADD UNIQUE KEY `post_pk` (`post_pk`);

--
-- Indeks for tabel `trends`
--
ALTER TABLE `trends`
  ADD UNIQUE KEY `trend_pk` (`trend_pk`);

--
-- Indeks for tabel `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_pk`),
  ADD UNIQUE KEY `user_pk` (`user_pk`),
  ADD UNIQUE KEY `user_email` (`user_email`),
  ADD UNIQUE KEY `user_name` (`user_username`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
